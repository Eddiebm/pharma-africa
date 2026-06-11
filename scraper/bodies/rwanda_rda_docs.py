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

PDFS = {
    "vet": BASE + "/monitoring-tool/documents-management/uploads/1/Registered-Products/1768297657_eRWANDA-FDA-VETERINARY-MEDICINAL-PRODUCTS-REGISTER-JULY-2025.pdf",
    "food": BASE + "/wp-content/uploads/2026/04/eREG-002_Food-Products-Register_09-APRIL2026.pdf",
}


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
                        source_url=PDFS["vet"],
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
                        source_url=PDFS["food"],
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
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            for label, url in PDFS.items():
                self.log(f"Downloading {label} PDF...")
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
