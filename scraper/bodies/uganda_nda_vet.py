"""
Uganda NDA — Veterinary Medicines Register
Source: Monthly PDF, same schema as human register.
URL pattern: https://www.nda.or.ug/wp-content/uploads/{YYYY}/{MM}/NATIONAL-DRUG-REGISTER-OF-UGANDA-VETERINARY-MEDICINES-{MONTH}-{YEAR}.pdf
Strategy: Try current month → previous months until one downloads. Parse with pdfplumber.
"""
import io
from datetime import date, timedelta
import httpx
import pdfplumber

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "UG"
REGISTER_PAGE = "https://www.nda.or.ug/drug-register/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)"}

MONTH_NAMES = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]


def _candidate_urls(months_back: int = 36) -> list[tuple[str, str]]:
    candidates = []
    seen: set[str] = set()
    today = date.today()
    for i in range(months_back):
        d = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        month_name = MONTH_NAMES[d.month - 1]
        mm = f"{d.month:02d}"
        base = (
            f"https://www.nda.or.ug/wp-content/uploads/{d.year}/{mm}/"
            f"NATIONAL-DRUG-REGISTER-OF-UGANDA-VETERINARY-MEDICINES-{month_name}-{d.year}"
        )
        for suffix in ("", "-1", "-2"):
            url = base + suffix + ".pdf"
            if url not in seen:
                seen.add(url)
                candidates.append((url, f"{month_name} {d.year}{suffix}"))
    return candidates


def _download_pdf(client: httpx.Client) -> tuple[bytes, str] | tuple[None, None]:
    for url, label in _candidate_urls():
        try:
            r = client.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200 and "pdf" in r.headers.get("content-type", ""):
                return r.content, label
        except Exception:
            continue
    return None, None


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration no", "nda reg"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["name of drug", "trade name", "brand", "product name"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["generic name", "inn", "active ingr"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["license holder", "holder", "manufacturer", "company"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["expiry", "renewal", "valid"]):
            mapping.setdefault("expiry", i)
        if any(x in hl for x in ["registration date", "reg date", "date"]):
            mapping.setdefault("reg_date", i)
    return mapping


def _parse_pdf(pdf_bytes: bytes, source_url: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        headers: list[str] = []
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue
                for row in table:
                    cells = [clean(str(c or "")) for c in row]
                    if not headers:
                        row_text = " ".join(cells).lower()
                        if any(x in row_text for x in ["drug", "product", "registration", "generic"]):
                            headers = cells
                        continue
                    if not any(cells):
                        continue
                    col = _map_columns(headers)

                    def get(key: str) -> str:
                        idx = col.get(key)
                        return cells[idx] if idx is not None and idx < len(cells) else ""

                    trade_name = get("trade_name") or None
                    inn_val = get("inn") or ""
                    if not inn_val and not trade_name:
                        continue
                    if inn_val.lower() in ("inn", "generic name", "name"):
                        continue

                    reg_no = get("reg_no") or None
                    expiry_raw = get("expiry") or get("reg_date") or None
                    exp = parse_date(expiry_raw)
                    status = "expired" if exp and exp < date.today() else "active"

                    records.append(RegistrationRecord(
                        inn=clean(inn_val) or clean(trade_name) or "",
                        brand_name=clean(trade_name),
                        country_code=COUNTRY_CODE,
                        registration_no="VET-" + clean(reg_no) if reg_no else None,
                        holder=clean(get("holder")) or None,
                        local_agent=None,
                        status=status,
                        expiry_date=exp,
                        dosage_forms=[clean(get("dosage_form"))] if get("dosage_form") else [],
                        source_url=source_url,
                        source_type="document",
                        raw=dict(zip(headers, cells)),
                    ))
    return records


class UgandaNDAVetScraper(BaseRegulatoryScraper):
    body_code = "NDA_UG_VET"
    country_code = COUNTRY_CODE
    source_url = REGISTER_PAGE

    def fetch(self) -> list[RegistrationRecord]:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            self.log("Looking for latest Uganda NDA veterinary register PDF...")
            pdf_bytes, label = _download_pdf(client)

        if not pdf_bytes:
            raise RuntimeError("Could not download any Uganda NDA vet PDF — all candidates failed")

        self.log(f"Parsing: {label} ({len(pdf_bytes) // 1024}KB)")
        records = _parse_pdf(pdf_bytes, REGISTER_PAGE)
        self.log(f"Parsed {len(records)} vet records")
        return records
