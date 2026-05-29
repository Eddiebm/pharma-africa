"""
Liberia Medicines and Health Products Regulatory Authority (LMRA)
This is the main government portal for Liberia, which does not appear to have a dedicated public drug search functionality.
The provided HTML snippet is for the Forestry Development Authority, not the LMRA.
Therefore, this scraper will return an empty list with a warning.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "LBR"
REGULATORY_BODY_NAME = "Liberia Medicines and Health Products Regulatory Authority"
PORTAL_URL = "https://www.fda.gov.lr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


class LiberiaScraper(BaseRegulatoryScraper):
    body_code = "LMRA_LBR"
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to access {self.source_url} for drug registration data.")
        try:
            with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
                resp = client.get(self.source_url)
                resp.raise_for_status()
                html = resp.text

            # Check if the page content suggests a drug register or just a general government portal.
            # The provided HTML snippet is for the Forestry Development Authority, which is not related to medicines.
            # We'll look for common indicators of a drug register, like keywords or specific link structures.
            soup = BeautifulSoup(html, "lxml")

            # A very basic check to see if this is likely a drug register.
            # If it's the Forestry Development Authority page or similar, it's not the target.
            if "Forestry Development Authority" in soup.title.string:
                self.warn("The portal appears to be the Forestry Development Authority, not a drug regulatory authority. No drug registration data found.")
                return []
            
            # Further checks could be added here if there were more specific indicators in the HTML
            # that differentiate a drug register from a general portal page.
            # For example, looking for links like "Product Register", "Search Drugs", etc.
            
            # If we reach here without finding explicit drug register content,
            # assume no public search is available.
            self.warn("No clear public drug search interface found on the portal. Returning empty list.")
            return []

        except httpx.RequestError as e:
            self.warn(f"Request to {self.source_url} failed: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred while processing {self.source_url}: {e}")
            return []
