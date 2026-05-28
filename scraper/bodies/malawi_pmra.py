"""
Malawi Pharmacy, Medicines and Poisons Board (PMRA) — Products Register
Source: Single static HTML table (no pagination, no AJAX)
  https://www.pmra.mw/products-register/
Columns: Product Name, Generic Name, Licence No, Dosage Form, Therapeutic Category, Date of Entry, Renewal Date
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "MW"
REGISTER_URL = "https://www.pmra.mw/products-register/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html",
}


def _parse_page(html: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(html, "lxml")

    table = soup.find("table")
    if not table:
        # Try finding a div with table-like structure
        table = soup.find(class_=re.compile(r"table|register|product", re.I))

    if not table:
        logging.warning("[PMRA_MW] No table found on products-register page")
        return records

    rows = table.find_all("tr")
    if len(rows) < 2:
        return records

    # Header row
    header_cells = rows[0].find_all(["th", "td"])
    headers = [clean(h.get_text()) for h in header_cells]
    col_map = _map_columns(headers)

    logging.info(f"[PMRA_MW] Headers: {headers}")

    for row in rows[1:]:
        cells = [clean(td.get_text()) for td in row.find_all("td")]
        if not cells or len(cells) < 2:
            continue

        def get(key: str) -> str:
            idx = col_map.get(key)
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx]

        product_name = get("product_name") or None
        generic_name = get("generic_name") or ""
        licence_no = get("licence_no") or None
        dosage_form = get("dosage_form") or ""
        renewal_raw = get("renewal") or None
        status_raw = get("status") or ""

        if not generic_name and not product_name:
            continue

        exp = parse_date(renewal_raw)
        if status_raw:
            status = normalize_status(status_raw)
        elif exp and exp < date.today():
            status = "expired"
        else:
            status = "active"

        records.append(RegistrationRecord(
            inn=clean(generic_name) or clean(product_name) or "",
            brand_name=clean(product_name),
            country_code=COUNTRY_CODE,
            registration_no=clean(licence_no),
            holder=None,
            local_agent=None,
            status=status,
            expiry_date=exp,
            dosage_forms=[clean(dosage_form)] if dosage_form else [],
            source_url=REGISTER_URL,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    return records


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["product name", "trade name", "brand"]):
            mapping.setdefault("product_name", i)
        if any(x in hl for x in ["generic name", "inn", "dci", "active ingr", "substance"]):
            mapping.setdefault("generic_name", i)
        if any(x in hl for x in ["licence", "license", "reg no", "registration"]):
            mapping.setdefault("licence_no", i)
        if any(x in hl for x in ["dosage form", "form", "presentation"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["renewal", "expiry", "expir"]):
            mapping.setdefault("renewal", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


class MalawiPMRAScraper(BaseRegulatoryScraper):
    body_code = "PMRA_MW"
    country_code = COUNTRY_CODE
    source_url = REGISTER_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Fetching Malawi PMRA products register...")
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(REGISTER_URL, headers=HEADERS)
            if resp.status_code != 200:
                raise RuntimeError(f"PMRA register page returned HTTP {resp.status_code}")

        records = _parse_page(resp.text)
        self.log(f"Parsed {len(records)} records")
        return records
