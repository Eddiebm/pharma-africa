"""
Tanzania Bureau of Standards (TBS) — Cosmetics + Food/Supplements registers
Source: Text-layer PDFs dynamically discovered from https://www.tbs.go.tz/pages/registered-products
Strategy: Fetch the registered-products page → find current PDF URLs by keyword → pdfplumber table extraction
"""
import io
import re
import httpx
import pdfplumber

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, clean

COUNTRY_CODE = "TZ"
BASE = "https://www.tbs.go.tz"
REGISTER_PAGE = BASE + "/pages/registered-products"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)"}


def _discover_pdfs(client: httpx.Client) -> dict[str, str]:
    """Return {"cosmetics": url, "food": url} by scraping the TBS registered-products page."""
    pdfs: dict[str, str] = {}
    try:
        resp = client.get(REGISTER_PAGE, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        html = resp.text
        for match in re.finditer(r'href=["\']([^"\']+\.pdf)["\']', html, re.IGNORECASE):
            href = match.group(1)
            url = href if href.startswith("http") else BASE + "/" + href.lstrip("/")
            upper = url.upper()
            if "COSMETIC" in upper and "cosmetics" not in pdfs:
                pdfs["cosmetics"] = url
            elif "FOOD" in upper and "food" not in pdfs:
                pdfs["food"] = url
    except Exception:
        pass

    # Fallback to known-good URLs if page scrape missed them
    if "cosmetics" not in pdfs:
        pdfs["cosmetics"] = BASE + "/uploads/files/REGISTERED%20COSMETIC%20PRODUCTS%20UP%20TO%20SEPTEMBER%202025.pdf"
    if "food" not in pdfs:
        pdfs["food"] = BASE + "/uploads/files/REGISTERED%20FOOD%20PRODUCTS%20UP%20TO%20FEB%202026.pdf"

    return pdfs


def _is_data_row(row: list) -> bool:
    if not row or not row[0]:
        return False
    return bool(re.match(r"\d+", str(row[0]).strip()))


def _parse_cosmetics(pdf_bytes: bytes) -> list[RegistrationRecord]:
    """
    Columns (TBS cosmetics register):
    S/N | Product Name | Product Type | Company/Applicant | Country | Reg Code | Expiry
    """
    records: list[RegistrationRecord] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not _is_data_row(row):
                        continue
                    try:
                        brand = clean(row[1]) if len(row) > 1 else None
                        category = clean(row[2]) if len(row) > 2 else None
                        holder = clean(row[3]) if len(row) > 3 else None
                        reg_no = clean(row[5]) if len(row) > 5 else None
                        expiry_raw = clean(row[6]) if len(row) > 6 else None
                    except Exception:
                        continue
                    if not brand:
                        continue
                    records.append(RegistrationRecord(
                        inn=category or "",
                        brand_name=brand,
                        country_code=COUNTRY_CODE,
                        registration_no="COSM-" + reg_no if reg_no else None,
                        holder=holder,
                        local_agent=None,
                        status="active",
                        expiry_date=parse_date(expiry_raw),
                        dosage_forms=[],
                        source_url=REGISTER_PAGE,
                        source_type="document",
                        raw={"row": [str(c) for c in row]},
                    ))
    return records


def _parse_food(pdf_bytes: bytes) -> list[RegistrationRecord]:
    """
    Columns (TBS food register):
    S/N | App No | Company | Brand Name | Common Name | Manufacturer | Country
    """
    records: list[RegistrationRecord] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not _is_data_row(row):
                        continue
                    try:
                        reg_no = clean(row[1]) if len(row) > 1 else None
                        holder = clean(row[2]) if len(row) > 2 else None
                        brand = clean(row[3]) if len(row) > 3 else None
                        common_name = clean(row[4]) if len(row) > 4 else None
                    except Exception:
                        continue
                    if not brand and not common_name:
                        continue
                    records.append(RegistrationRecord(
                        inn=common_name or "",
                        brand_name=brand,
                        country_code=COUNTRY_CODE,
                        registration_no="FOOD-" + reg_no if reg_no else None,
                        holder=holder,
                        local_agent=None,
                        status="active",
                        expiry_date=None,
                        dosage_forms=[],
                        source_url=REGISTER_PAGE,
                        source_type="document",
                        raw={"row": [str(c) for c in row]},
                    ))
    return records


class TanzaniaTBSScraper(BaseRegulatoryScraper):
    body_code = "TBS_TZ"
    country_code = COUNTRY_CODE
    source_url = REGISTER_PAGE

    def fetch(self) -> list[RegistrationRecord]:
        records: list[RegistrationRecord] = []
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            pdfs = _discover_pdfs(client)
            self.log(f"Discovered PDFs: {list(pdfs.keys())}")
            for label, url in pdfs.items():
                self.log(f"Downloading {label} PDF from {url}")
                try:
                    resp = client.get(url, headers=HEADERS, timeout=120)
                    resp.raise_for_status()
                except Exception as e:
                    self.log(f"  {label}: download failed — {e}")
                    continue
                if label == "cosmetics":
                    recs = _parse_cosmetics(resp.content)
                else:
                    recs = _parse_food(resp.content)
                self.log(f"  {label}: {len(recs)} records")
                records.extend(recs)
        self.log(f"Total Tanzania TBS: {len(records)}")
        return records
