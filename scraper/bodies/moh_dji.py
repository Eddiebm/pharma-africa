"""
Ministry of Health Djibouti (MOH)
Portal URL: https://www.sante.gouv.dj
Strategy: The portal appears to be a static government website without a direct drug registration search feature.
It contains information about the ministry, its organization, and some general health topics (like HIV/AIDS).
There is no discernible API or dynamic content that lists registered pharmaceutical products.
Therefore, this scraper will return an empty list and log a warning.
"""

import logging
import sys
import os
from datetime import date

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "DJI"
BODY_CODE = "MOH_DJI"
SOURCE_URL = "https://www.sante.gouv.dj"

class DjiboutiScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Accessing {self.source_url}")

        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(self.source_url)
                resp.raise_for_status()
                html = resp.text
                soup = BeautifulSoup(html, "lxml")

                # Check for any potential links or sections related to drug registration.
                # Based on the provided HTML, there are no such links or obvious data tables.
                # The website seems to be a general information portal for the ministry.

                # If no search or data is found, log a warning and return empty.
                # A more thorough inspection might reveal hidden APIs or forms,
                # but for now, we assume no public drug register is available.

                self.warn("No public drug registration search interface found on the Ministry of Health Djibouti portal.")
                return []

        except httpx.RequestError as e:
            self.warn(f"Request failed: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred: {e}")
            return []
