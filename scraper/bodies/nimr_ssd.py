"""
National Institute for Medical Research (NIMR) South Sudan
Portal URL: https://www.moh.gov.ss

The provided HTML snippet shows the homepage of the Ministry of Health (MOH) of South Sudan.
It contains links for 'Home', 'About', and potentially other sections but does not appear
to host a searchable database of registered pharmaceutical products.
There is no visible search bar or link to a product registration portal.

Based on this, it's highly probable that there isn't a public API or a searchable table
of registered drugs directly accessible through this website.

Strategy:
Since no public product registration portal is found, the scraper will log a warning
and return an empty list.
"""

import logging
import httpx
from bs4 import BeautifulSoup
from datetime import date

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "SSD"
BODY_CODE = "NIMR_SSD"
SOURCE_URL = "https://www.moh.gov.ss"
PORTAL_TYPE = "homepage" # Indicate that this is a homepage, not a searchable portal

def _parse_html_for_data(html: str, source_url: str) -> list[RegistrationRecord]:
    """
    This function is a placeholder as the current portal does not appear to have
    a searchable product registration table. If a portal were found with a table,
    this function would parse it.
    """
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(html, "lxml")

    # Example: If a table with id="productTable" existed, we'd parse it here.
    # table = soup.find("table", {"id": "productTable"})
    # if table:
    #     rows = table.find_all("tr")
    #     if len(rows) > 1:
    #         headers = [clean(th.get_text()) for th in rows[0].find_all(["th", "td"])]
    #         col_map = _map_columns(headers) # Assume _map_columns is defined
    #         for row in rows[1:]:
    #             cells = [clean(td.get_text()) for td in row.find_all("td")]
    #             # ... parsing logic ...
    #             # records.append(RegistrationRecord(...))
    # else:
    #     logging.warning(f"[{BODY_CODE}] No product table found on the page.")

    return records

def _map_columns(headers: list[str]) -> dict[str, int]:
    """
    Placeholder for mapping table headers to RegistrationRecord fields.
    This would be implemented if a table structure was identified.
    """
    mapping: dict[str, int] = {}
    # Example mapping:
    # for i, h in enumerate(headers):
    #     hl = h.lower()
    #     if "registration number" in hl: mapping.setdefault("reg_no", i)
    #     if "product name" in hl: mapping.setdefault("trade_name", i)
    #     if "inn" in hl: mapping.setdefault("inn", i)
    #     if "dosage form" in hl: mapping.setdefault("dosage_form", i)
    #     if "holder" in hl: mapping.setdefault("holder", i)
    #     if "expiry date" in hl: mapping.setdefault("expiry", i)
    #     if "status" in hl: mapping.setdefault("status", i)
    return mapping


class SouthSudanScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to scrape: {self.source_url}")

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            try:
                response = client.get(self.source_url)
                response.raise_for_status()
                html_content = response.text

                # Check the content type to ensure it's HTML
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    self.warn(f"Expected HTML content, but received: {content_type}")
                    return []

                # Based on initial inspection, this URL appears to be a homepage
                # and not a portal with a searchable drug register.
                self.warn(f"[{self.body_code}] No public drug registration portal found at {self.source_url}. Returning empty list.")
                return []

            except httpx.RequestError as e:
                self.warn(f"HTTP request failed: {e}")
                return []
            except Exception as e:
                self.warn(f"An unexpected error occurred: {e}")
                return []
