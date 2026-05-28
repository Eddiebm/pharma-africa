"""
Madagascar — AGMED (Agence du Médicament de Madagascar)
Monthly PDFs: https://amm.mg/PDF/SE/YYYY/[N] LISTE_AMM_[Month]-YYYY.pdf
Columns: Nom commercial, DCI, Présentation, Fabriquant, Laboratoire
Uses pdfplumber to extract tables from each page.
"""
import io
import logging
from datetime import date

import httpx
import pdfplumber

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import clean

COUNTRY_CODE = "MG"
SOURCE_URL   = "https://amm.mg"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)"}

# Month names in French as used in filenames
MONTHS = [
    "Janv", "Fevr", "Mars", "Avri", "Mai", "Juin",
    "Juil", "Aout", "Sept", "Octo", "Nove", "Dece",
]


def _candidate_urls(years_back: int = 3) -> list[str]:
    """Generate candidate PDF URLs newest-first across multiple years."""
    from datetime import datetime
    now = datetime.now()
    urls = []
    for year_offset in range(years_back):
        year = now.year - year_offset
        # Try months newest-first
        for month_idx in range(12, 0, -1):
            month_name = MONTHS[month_idx - 1]
            url = (
                f"https://amm.mg/PDF/SE/{year}/"
                f"{month_idx}%20LISTE_AMM_{month_name}-{year}.pdf"
            )
            urls.append(url)
    return urls


def _find_latest_pdf(client: httpx.Client) -> tuple[str, bytes] | None:
    """Try candidate URLs until we find one that returns a valid PDF."""
    for url in _candidate_urls():
        try:
            r = client.head(url, timeout=10)
            if r.status_code == 200:
                logging.info(f"[AMM_MG] Found PDF: {url}")
                r2 = client.get(url, timeout=60)
                r2.raise_for_status()
                if r2.content[:4] == b"%PDF" or len(r2.content) > 100_000:
                    return url, r2.content
        except Exception as e:
            logging.debug(f"[AMM_MG] {url}: {e}")
    return None


def _parse_pdf(pdf_bytes: bytes, source_url: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        logging.info(f"[AMM_MG] PDF has {len(pdf.pages)} pages")

        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Detect header row
                header_row = table[0]
                if not header_row:
                    continue

                headers = [clean(str(c or "")).lower() for c in header_row]
                col: dict[str, int] = {}
                for i, h in enumerate(headers):
                    if "nom" in h and "commercial" in h:
                        col.setdefault("brand", i)
                    elif "dci" in h or "dénomination" in h:
                        col.setdefault("inn", i)
                    elif "présentation" in h or "presentation" in h:
                        col.setdefault("form", i)
                    elif "fabriquant" in h or "fabricant" in h:
                        col.setdefault("manufacturer", i)
                    elif "laboratoire" in h or "labo" in h:
                        col.setdefault("holder", i)

                if "brand" not in col and "inn" not in col:
                    continue

                for row in table[1:]:
                    if not row or all(not c for c in row):
                        continue

                    def get(key: str) -> str:
                        idx = col.get(key)
                        if idx is None or idx >= len(row):
                            return ""
                        val = str(row[idx] or "")
                        # Take first line only (PDF rendering sometimes merges cells)
                        return clean(val.split("\n")[0])

                    brand   = get("brand")
                    inn_val = get("inn")
                    form    = get("form")
                    holder  = get("holder") or get("manufacturer")

                    if not inn_val and not brand:
                        continue

                    records.append(RegistrationRecord(
                        inn=inn_val or brand,
                        brand_name=brand or None,
                        country_code=COUNTRY_CODE,
                        registration_no=None,
                        holder=holder or None,
                        local_agent=None,
                        status="active",
                        expiry_date=None,
                        dosage_forms=[form] if form else [],
                        source_url=source_url,
                        source_type="document",
                        raw={
                            "brand": brand, "inn": inn_val,
                            "form": form, "holder": holder,
                        },
                    ))

    return records


class MadagascarAMMScraper(BaseRegulatoryScraper):
    body_code = "AMM_MG"
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> list[RegistrationRecord]:
        with httpx.Client(
            verify=False,
            follow_redirects=True,
            timeout=60,
            headers=HEADERS,
        ) as client:
            result = _find_latest_pdf(client)
            if not result:
                self.warn("No Madagascar AMM PDF found — all candidate URLs returned 404")
                return []

            url, pdf_bytes = result
            self.log(f"Parsing PDF: {url} ({len(pdf_bytes):,} bytes)")
            records = _parse_pdf(pdf_bytes, url)

        self.log(f"Total fetched: {len(records)}")
        return records
