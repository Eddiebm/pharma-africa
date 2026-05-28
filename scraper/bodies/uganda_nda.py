"""
Uganda National Drug Authority (NDA) — Human Medicines Register
Source: Monthly PDF at https://www.nda.or.ug/drug-register/
PDF URL pattern: https://www.nda.or.ug/wp-content/uploads/{YYYY}/{MM}/NATIONAL-DRUG-REGISTER-OF-UGANDA-HUMAN-MEDICINES-{MONTH}-{YEAR}.pdf
Strategy: Try current month → previous months until one downloads. Parse with pdfplumber.
"""
import io
import re
import logging
from datetime import date, timedelta
import httpx
import pdfplumber

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "UG"
BASE_SITE = "https://www.nda.or.ug"
REGISTER_PAGE = "https://www.nda.or.ug/drug-register/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
}

MONTH_NAMES = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]


def _candidate_urls(months_back: int = 36) -> list[tuple[str, str]]:
    """Generate (url, label) pairs for recent months, newest first."""
    candidates = []
    today = date.today()
    for i in range(months_back):
        d = today.replace(day=1) - timedelta(days=i * 28)
        # normalize to first of month
        d = d.replace(day=1)
        year = d.year
        month_idx = d.month
        month_name = MONTH_NAMES[month_idx - 1]
        mm = f"{month_idx:02d}"
        url = (
            f"https://www.nda.or.ug/wp-content/uploads/{year}/{mm}/"
            f"NATIONAL-DRUG-REGISTER-OF-UGANDA-HUMAN-MEDICINES-{month_name}-{year}.pdf"
        )
        label = f"{month_name} {year}"
        candidates.append((url, label))
    # deduplicate (timedelta can repeat months)
    seen: set[str] = set()
    unique = []
    for u, l in candidates:
        if u not in seen:
            seen.add(u)
            unique.append((u, l))
    return unique


def _download_pdf(client: httpx.Client) -> tuple[bytes, str] | tuple[None, None]:
    """Return (pdf_bytes, label) for the most recent available PDF."""
    # First try scraping the register page for direct links
    try:
        resp = client.get(REGISTER_PAGE, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            import re
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "HUMAN-MEDICINES" in href.upper() and href.endswith(".pdf"):
                    full = href if href.startswith("http") else BASE_SITE + href
                    try:
                        r2 = client.get(full, headers=HEADERS, timeout=60)
                        if r2.status_code == 200 and r2.headers.get("content-type", "").startswith("application/pdf"):
                            return r2.content, a.get_text().strip() or full
                    except Exception:
                        pass
    except Exception:
        pass

    # Fallback: try candidate URLs (including variant with -1 suffix for July 2024)
    all_candidates = []
    for url, label in _candidate_urls():
        all_candidates.append((url, label))
        # Some months have a -1 suffix variant
        all_candidates.append((url.replace(".pdf", "-1.pdf"), label + " (v2)"))

    for url, label in all_candidates:
        try:
            r = client.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"):
                logging.info(f"[NDA_UG] Found PDF: {label} — {url}")
                return r.content, label
        except Exception:
            continue

    return None, None


def _parse_pdf(pdf_bytes: bytes, source_url: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        headers: list[str] = []

        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                for row_idx, row in enumerate(table):
                    if not row:
                        continue
                    cells = [clean(str(c or "")) for c in row]

                    # Detect header row
                    if not headers:
                        row_text = " ".join(cells).lower()
                        if any(x in row_text for x in ["product", "drug", "trade name", "inn", "ingredient", "registration"]):
                            headers = cells
                            continue

                    if not headers or not any(cells):
                        continue

                    col_map = _map_columns(headers)

                    def get(key: str) -> str:
                        idx = col_map.get(key)
                        if idx is None or idx >= len(cells):
                            return ""
                        return cells[idx]

                    reg_no = get("reg_no") or None
                    trade_name = get("trade_name") or None
                    inn_val = get("inn") or ""
                    dosage_form = get("dosage_form") or ""
                    holder = get("holder") or None
                    expiry_raw = get("expiry") or None
                    status_raw = get("status") or ""

                    if not inn_val and not trade_name:
                        continue
                    # Skip header-like rows that repeat
                    if inn_val.lower() in ("inn", "generic name", "active ingredient", "name"):
                        continue

                    exp = parse_date(expiry_raw)
                    if status_raw:
                        status = normalize_status(status_raw)
                    elif exp and exp < date.today():
                        status = "expired"
                    else:
                        status = "active"

                    records.append(RegistrationRecord(
                        inn=clean(inn_val) or clean(trade_name) or "",
                        brand_name=clean(trade_name),
                        country_code=COUNTRY_CODE,
                        registration_no=clean(reg_no),
                        holder=clean(holder),
                        local_agent=None,
                        status=status,
                        expiry_date=exp,
                        dosage_forms=[clean(dosage_form)] if dosage_form else [],
                        source_url=source_url,
                        source_type="document",
                        raw=dict(zip(headers, cells)),
                    ))

    return records


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration no", "reg. no", "product no"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["trade name", "product name", "brand", "commercial"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["inn", "generic", "active ingr", "api", "substance"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form", "presentation"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["holder", "manufacturer", "company", "applicant"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["expiry", "renewal", "valid"]):
            mapping.setdefault("expiry", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


class UgandaNDAScraper(BaseRegulatoryScraper):
    body_code = "NDA_UG"
    country_code = COUNTRY_CODE
    source_url = REGISTER_PAGE

    def fetch(self) -> list[RegistrationRecord]:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            self.log("Looking for latest Uganda drug register PDF...")
            pdf_bytes, label = _download_pdf(client)

        if not pdf_bytes:
            raise RuntimeError("Could not download any Uganda NDA PDF — all candidates failed")

        self.log(f"Parsing PDF: {label} ({len(pdf_bytes)//1024}KB)")
        records = _parse_pdf(pdf_bytes, REGISTER_PAGE)
        self.log(f"Parsed {len(records)} records")
        return records
