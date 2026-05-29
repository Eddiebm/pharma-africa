"""
National Centre for Medical Supplies (NCMS) Libya
Portal: https://www.ncms.org.ly
The NCMS website appears to be a static informational site with no direct drug search functionality.
There is no publicly accessible API or searchable database for registered medicines.
Therefore, this scraper will return an empty list and log a warning.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "LBY"
PORTAL_URL = "https://www.ncms.org.ly"
BODY_CODE = "NCMS_LBY"


def _map_columns(headers: list[str]) -> dict[str, int]:
    """Map headers to standard field names."""
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
    """
    This function is a placeholder. Since the target portal does not have
    a searchable drug register, this will not be used.
    """
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
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


class LibyaScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Accessing portal: {self.source_url}")

        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(self.source_url)
                resp.raise_for_status()

            # Check if the portal is just a static homepage without a searchable database
            # A simple check for common elements of a dynamic search page can be done here.
            # If no such elements are found, assume it's a static informational site.
            soup = BeautifulSoup(resp.text, "lxml")

            # Example check: Look for search input fields or specific JavaScript-driven content
            # that suggests a dynamic data table or search interface.
            # If these are absent, it's likely a static page.
            has_search_elements = soup.find('input', {'type': 'text'}) or \
                                  soup.find('table', {'class': re.compile('datatable|table-bordered|searchable')}) or \
                                  soup.find('form', {'id': re.compile('search-form|filter-form')})

            if not has_search_elements:
                self.warn("The NCMS portal appears to be a static informational site without a public drug search functionality.")
                self.warn("Returning an empty list of records.")
                return []

            # If there were search elements, we would proceed to implement search queries,
            # pagination, etc. as seen in the example scrapers.
            # For this specific case, as per the observed portal, we return empty.

        except httpx.RequestError as e:
            self.warn(f"Failed to connect to {self.source_url}: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred while processing {self.source_url}: {e}")
            return []

        return [] # Return empty list if no search functionality is found