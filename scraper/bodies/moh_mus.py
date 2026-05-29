"""
Ministry of Health Mauritius (MOH)
Portal: https://health.govmu.org
No visible public drug registration search. The provided URL is the general ministry homepage.
Therefore, no data can be scraped.
"""

import logging
import httpx
from bs4 import BeautifulSoup
from datetime import date

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "MUS"
PORTAL_URL = "https://health.govmu.org"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


class MauritiusScraper(BaseRegulatoryScraper):
    body_code = "MOH_MUS"
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Accessing {PORTAL_URL}")

        try:
            with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
                resp = client.get(PORTAL_URL)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "lxml")

                # Attempt to find any search or registration link, if not, assume no public data.
                # A thorough manual inspection would be needed to confirm this definitively.
                # Based on the provided HTML, there isn't an obvious drug search form or link.
                search_links = soup.find_all('a', string=lambda t: t and "register" in t.lower())
                if not search_links:
                    search_links = soup.find_all('a', href=lambda h: h and "product" in h.lower())
                
                if not search_links:
                    self.warn("No discernible public drug registration search functionality found on the portal.")
                    self.warn("The portal appears to be a general ministry homepage without a public drug register.")
                    return []

                # If we found potential links, we would proceed to scrape them.
                # For now, assuming no direct drug search based on initial HTML.
                self.warn("Potential registration links found, but no specific drug search interface detected. Returning empty.")
                return []

        except httpx.RequestError as e:
            self.warn(f"Network error accessing {PORTAL_URL}: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred: {e}")
            return []

    def _parse_registration_record(self, row: dict, source_url: str) -> RegistrationRecord:
        """
        Placeholder for parsing a single registration record.
        This method would be implemented if actual data extraction was possible.
        """
        # This is a dummy implementation as no data is expected to be scraped.
        raise NotImplementedError("Data parsing logic is not applicable as no search is found.")
