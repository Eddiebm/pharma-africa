"""
Burundi Ministry of Public Health and Fight Against AIDS (Bufmar)
The provided URL (https://www.mspls.gov.bi) appears to be a general government portal and not a specific drug registration database.
A direct search for a drug registration portal or API for Burundi's regulatory body (BUFMAR) has not yielded a publicly accessible interface.
Therefore, this scraper will return an empty list with a warning.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "BDI"
# The provided URL is a general government portal and does not appear to host a drug registration database.
# A dedicated portal or API for BUFMAR has not been identified.
REGISTRATION_PORTAL_URL = "https://www.mspls.gov.bi"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


class BurundiScraper(BaseRegulatoryScraper):
    body_code = "BUFMAR_BDI"
    country_code = COUNTRY_CODE
    source_url = REGISTRATION_PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Accessing {self.source_url}")
        self.warn("No direct drug registration portal or API found for Burundi (BUFMAR). Returning empty list.")
        # If a specific drug search URL was identified, it would be used here.
        # Example:
        # try:
        #     with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        #         # Attempt to find a registration table or API endpoint
        #         # This would involve parsing the HTML or making API calls if available.
        #         # For now, assuming no direct access.
        #         pass
        # except Exception as e:
        #     self.log(f"An error occurred while trying to access {self.source_url}: {e}")
        return []
