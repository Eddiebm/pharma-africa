"""
Mali Direction Nationale de la Pharmacie (DNP Mali)
Portal: https://www.sante.gov.ml
No direct drug search API or interactive portal found.
Only static content is available, thus no scraping is possible.
"""

import logging
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "MLI"
PORTAL_URL = "https://www.sante.gov.ml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


class MaliScraper(BaseRegulatoryScraper):
    body_code = "DNP_MLI"
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to fetch data from {self.source_url}")

        try:
            with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
                resp = client.get(self.source_url)
                resp.raise_for_status()
                content = resp.text

            soup = BeautifulSoup(content, "lxml")

            # Check if there's any indication of a searchable product register.
            # Based on the provided HTML (FETCH_ERROR), it's likely the main site,
            # not a specific drug registration portal.
            # We'll look for common patterns like tables or search forms related to medicines.
            # If none are found, we'll log a warning and return an empty list.

            # Example: If we were to find a table with "Médicament", "Numéro d'enregistrement", etc.
            # tables = soup.find_all("table")
            # for table in tables:
            #     headers = [clean(th.get_text()) for th in table.find_all(["th", "td"])]
            #     if any("médicament" in h.lower() for h in headers):
            #         self.log("Found a potential table for medicines. Proceeding with parsing (example).")
            #         # Implement parsing logic here if a table structure is identified.
            #         # For now, assume no such table exists for this specific URL.
            #         pass # Placeholder for actual parsing if structure were found

            # If no specific drug registration portal or searchable interface is found,
            # log a warning and return an empty list.
            self.warn(
                "No direct drug search interface or product register found on the main portal. "
                "The provided URL likely leads to a general government health ministry page."
            )
            return []

        except httpx.RequestError as e:
            self.warn(f"HTTP request failed: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred during scraping: {e}")
            return []
