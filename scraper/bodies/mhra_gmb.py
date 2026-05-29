"""
Medicines and Health Regulatory Authority (MHRA), Gambia.
The provided HTML is for the Ministry of Health homepage, and there's no apparent public drug registration portal linked or accessible from it.
Therefore, this scraper will return an empty list and log a warning.
"""

import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "GMB"
PORTAL_URL = "https://www.moh.gov.gm/"
BODY_CODE = "MHRA_GMB"


def _map_columns(headers: list[str]) -> dict[str, int]:
    """Maps table headers to expected keys. Basic mapping for potential future use."""
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration no", "product reg", "licence no", "license no"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["trade name", "product name", "product trade", "brand"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["inn", "api", "active ingr", "generic name"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["mah", "manufacturer", "company", "applicant", "holder"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["local tech", "local rep", "representative"]):
            mapping.setdefault("local_rep", i)
        if any(x in hl for x in ["expiry", "expir", "renewal"]):
            mapping.setdefault("expiry", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping

def _parse_html(html: str, source_url: str) -> list[RegistrationRecord]:
    """Placeholder for parsing potential table data if found."""
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table") # Attempt to find any table
    if not table:
        return records

    rows = table.find_all("tr")
    if len(rows) < 2:
        return records

    headers = [clean(th.get_text()) for th in rows[0].find_all(["th", "td"])]
    col_map = _map_columns(headers)

    for row in rows[1:]:
        cells = [clean(td.get_text()) for td in row.find_all("td")]
        if not cells or len(cells) < 2:
            continue

        def get(key: str) -> str:
            idx = col_map.get(key)
            return cells[idx] if idx is not None and idx < len(cells) else ""

        reg_no      = get("reg_no") or None
        trade_name  = get("trade_name") or None
        inn_val     = get("inn") or ""
        dosage_form = get("dosage_form") or ""
        holder      = get("holder") or None
        local_rep   = get("local_rep") or None
        expiry_raw  = get("expiry") or None
        status_raw  = get("status") or ""

        if not inn_val and not trade_name:
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
            local_agent=clean(local_rep),
            status=status,
            expiry_date=exp,
            dosage_forms=[clean(dosage_form)] if dosage_form else [],
            source_url=source_url,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))
    return records


class GambiaScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to access Gambia Ministry of Health portal at {self.source_url}")
        self.log("The provided HTML suggests a general ministry homepage, not a specific drug registration portal.")
        self.log("No drug search functionality or accessible product registration database found.")

        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(self.source_url)
                resp.raise_for_status()
                # Even though we don't expect to find data, we try to parse if any table exists.
                # In this specific case, the provided HTML doesn't seem to contain a search form.
                records = _parse_html(resp.text, self.source_url)

                if not records:
                    self.warn("No drug registration data found on the portal.")
                return records

        except httpx.RequestError as e:
            self.warn(f"Request error while fetching {self.source_url}: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred: {e}")
            return []
