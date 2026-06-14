"""
Rwanda FDA — additional registers via PDF download
Sources:
  Veterinary Medicinal Products: monitoring-tool/documents-management/...VETERINARY-MEDICINAL-PRODUCTS-REGISTER-JULY-2025.pdf
  Food Products Register: wp-content/uploads/2026/04/eREG-002_Food-Products-Register_09-APRIL2026.pdf
Strategy: Download PDFs → pdfplumber table extraction → upsert into registrations
"""
import re
import sys
import os
import io
import httpx
import pdfplumber

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, clean

COUNTRY_CODE = "RW"
BASE = "https://rwandafda.gov.rw"

VET_PAGE  = BASE + "/veterinary-registration-registered-products-2/"
FOOD_PAGE = BASE + "/food-registered-products/"

def _discover_pdfs(client: httpx.Client) -> dict:
    pdfs = {}
    specs = [
        ("vet",  VET_PAGE,  "VETERINARY-MEDICINAL-PRODUCTS-REGISTER"),
        ("food", FOOD_PAGE, "Food-Products-Register"),
    ]
    for key, page_url, pattern in specs:
        resp = client.get(page_url)
        resp.raise_for_status()
        html = resp.text
        pos = 0
        while pos < len(html):
            dot_pdf = html.lower().find(".pdf", pos)
            if dot_pdf < 0:
                break
            quote_start = max(html.rfind('"', 0, dot_pdf), html.rfind("'", 0, dot_pdf))
            if quote_start >= 0:
                link = html[quote_start + 1: dot_pdf + 4]
                if pattern.lower() in link.lower():
                    pdfs[key] = link if link.startswith("http") else BASE + "/" + link.lstrip("/")
                    break
            pos = dot_pdf + 4
    return pdfs


def _is_data_row(row):
    if not row or not row[0]:
        return False
    return bool(re.match(r"\d+", str(row[0]).strip()))


def _parse_vet(pdf_bytes: bytes) -> list[RegistrationRecord]:
    records = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages[1:]:  # skip cover page
            for table in page.extract_tables():
                for row in table:
                    if not _is_data_row(row):
                        continue
                    try:
                        reg_no = clean(row[1]) if len(row) > 1 else None
                        brand = clean(row[2]) if len(row) > 2 else None
                        inn = clean(row[3]) if len(row) > 3 else None
                        dosage = clean(row[5]) if len(row) > 5 else None
                        holder = clean(row[11]) if len(row) > 11 else None
                        expiry_raw = clean(row[14]) if len(row) > 14 else None
                    except Exception:
                        continue
                    if not brand and not reg_no:
                        continue
                    records.append(RegistrationRecord(
                        inn=inn or "",
                        brand_name=brand,
                        country_code=COUNTRY_CODE,
                        registration_no="VET-" + reg_no if reg_no else None,
                        holder=holder,
                        local_agent=None,
                        status="active",
                        expiry_date=parse_date(expiry_raw),
                        dosage_forms=[dosage] if dosage else [],
                        source_url=VET_PAGE,
                        source_type="document",
                        raw={"row": [str(c) for c in row]},
                    ))
    return records


def _parse_food(pdf_bytes: bytes) -> list[RegistrationRecord]:
    records = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not _is_data_row(row):
                        continue
                    try:
                        reg_no = clean(row[1]) if len(row) > 1 else None
                        brand = clean(row[2]) if len(row) > 2 else None
                        classification = clean(row[3]) if len(row) > 3 else None
                        holder = clean(row[5]) if len(row) > 5 else None
                        expiry_raw = clean(row[9]) if len(row) > 9 else None
                    except Exception:
                        continue
                    if not brand and not reg_no:
                        continue
                    records.append(RegistrationRecord(
                        inn=classification or "",
                        brand_name=brand,
                        country_code=COUNTRY_CODE,
                        registration_no="FOOD-" + reg_no if reg_no else None,
                        holder=holder,
                        local_agent=None,
                        status="active",
                        expiry_date=parse_date(expiry_raw),
                        dosage_forms=[],
                        source_url=FOOD_PAGE,
                        source_type="document",
                        raw={"row": [str(c) for c in row]},
                    ))
    return records


class RwandaRDADocsScraper(BaseRegulatoryScraper):
    body_code = "RDA_RW_DOCS"
    country_code = COUNTRY_CODE
    source_url = BASE

    def fetch(self) -> list[RegistrationRecord]:
        records = []
        with httpx.Client(timeout=120, follow_redirects=True, verify=False) as client:
            pdfs = _discover_pdfs(client)
            if not pdfs:
                self.log("No PDFs discovered — skipping")
                return []
            for label, url in pdfs.items():
                self.log(f"Downloading {label} PDF from {url}")
                resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                data = resp.content
                if label == "vet":
                    recs = _parse_vet(data)
                else:
                    recs = _parse_food(data)
                self.log(f"  {label}: {len(recs)} records")
                records.extend(recs)
        self.log(f"Total Rwanda docs: {len(records)}")
        return records
