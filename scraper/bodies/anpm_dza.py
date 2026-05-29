"""
Agence Nationale des Produits Médicaux (ANPM) - Algeria
Portal: https://www.anpm.dz

The portal's main page (https://www.anpm.dz) does not appear to have a public drug search functionality.
It primarily contains information about the agency itself and news.
Therefore, this scraper will return an empty list with a warning.
"""

import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup
import os
import sys

# Assuming base.py and normalize.py are in the parent directory or accessible via sys.path
# If not, you might need to adjust the import path.
try:
    from base import BaseRegulatoryScraper, RegistrationRecord
    from normalize import parse_date, normalize_status, clean
except ImportError:
    # Fallback for testing purposes if run directly
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from base import BaseRegulatoryScraper, RegistrationRecord
    from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "DZA"
BODY_CODE = "ANPM_DZA"
PORTAL_URL = "https://www.anpm.dz"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": PORTAL_URL,
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-GPC": "1",
}


class AlgeriaScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Accessing {PORTAL_URL} to check for drug registration portal.")

        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(PORTAL_URL, headers=HEADERS)
                resp.raise_for_status()
                html = resp.text
                soup = BeautifulSoup(html, "lxml")

                # The ANPM website does not appear to have a public search interface for registered products.
                # We'll log a warning and return an empty list.
                if "Agence Nationale des Produits Médicaux" in soup.title.string:
                    self.warn(
                        "The ANPM portal does not seem to offer a public drug registration search interface. "
                        "Returning an empty list. Further investigation of potential sub-sections or "
                        "alternative portals might be required if a search function exists elsewhere."
                    )
                    return []

        except httpx.RequestError as e:
            self.warn(f"Request to {PORTAL_URL} failed: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred while checking {PORTAL_URL}: {e}")
            return []

        # If by any chance a search interface was found, this part would be implemented.
        # Since it's not apparent, we exit.
        return []