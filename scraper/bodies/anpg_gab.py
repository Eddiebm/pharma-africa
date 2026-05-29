"""
Gabon National Agency for Pharmacies (ANPG)
Portal URL: https://www.sante.gouv.ga/
Strategy: The website appears to be a general government portal and does not
          contain a readily accessible public database for registered pharmaceutical products.
          A search for drug registrations within the provided HTML could not be identified.
          Therefore, this scraper will return an empty list with a warning.
"""

import logging
import httpx
from bs4 import BeautifulSoup
from datetime import date
from typing import Optional, List

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "GAB"
BODY_CODE = "ANPG_GAB"
SOURCE_URL = "https://www.sante.gouv.ga/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


class GabonScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> List[RegistrationRecord]:
        self.log(f"Accessing {self.source_url}")

        try:
            with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
                resp = client.get(self.source_url)
                resp.raise_for_status()
                html = resp.text
                soup = BeautifulSoup(html, "lxml")

                # Check if there's any indication of a drug registry or search form
                # Based on the provided HTML, there isn't.
                # Common patterns to look for: forms with input fields for product name, registration number, etc.
                # or links explicitly mentioning "pharmaceutical products", "drug registration", etc.
                # The current HTML mainly shows government institutions and ministry links.

                # If no discernible drug registry search is found, log a warning and return empty.
                if not self._has_drug_registry_elements(soup):
                    self.warn("No public drug registration search or database found on the provided portal.")
                    return []

                # If a search form *were* found, the logic to iterate through search queries
                # and parse results would go here. For now, assume no search is available.

        except httpx.RequestError as e:
            self.warn(f"HTTP request failed: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred: {e}")
            return []

        return [] # Default return if no records are found and no specific search mechanism is implemented.

    def _has_drug_registry_elements(self, soup: BeautifulSoup) -> bool:
        """
        Helper method to check if the page contains elements that suggest a drug registry search.
        This is a heuristic and may need adjustment if the portal structure changes.
        """
        # Look for common keywords or form structures that might indicate a drug registry search.
        # Based on the provided HTML, this is unlikely to find anything.
        potential_search_keywords = ["médicament", "produit pharmaceutique", "enregistrement", "registre", "autorisé", "princeps"]
        forms = soup.find_all("form")
        for form in forms:
            form_text = form.get_text().lower()
            if any(keyword in form_text for keyword in potential_search_keywords):
                return True
            # Also check for common input field names or IDs
            inputs = form.find_all("input", {"name": re.compile(r"nom_produit|reference|inn|designation", re.IGNORECASE)})
            if inputs:
                return True
        return False
