"""
Ministry of Health São Tomé and Príncipe (MOH_STP)

Portal URL: https://www.minsaude.gov.st

Strategy:
The provided HTML indicates that the website is inaccessible due to an "Account disabled by server administrator."
Therefore, it's impossible to scrape any registration data from this portal.
The scraper will log a warning and return an empty list.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "STP"
PORTAL_URL = "https://www.minsaude.gov.st"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


class SãoToméandPríncipeScraper(BaseRegulatoryScraper):
    body_code = "MOH_STP"
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to fetch data from {PORTAL_URL}")

        try:
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                resp = client.get(PORTAL_URL, headers=HEADERS)
                resp.raise_for_status()
                html = resp.text

                if "Account disabled by server administrator." in html:
                    self.warn(
                        "The Ministry of Health São Tomé and Príncipe portal is inaccessible due to an 'Account disabled' error. "
                        "No data can be scraped."
                    )
                    return []
                else:
                    # If somehow the error message is not present, attempt to parse, though unlikely to succeed.
                    # This part is unlikely to be reached given the provided HTML.
                    soup = BeautifulSoup(html, "lxml")
                    # Add parsing logic here if the portal structure was different and accessible.
                    # For now, we assume the error is present and return empty.
                    self.log("Portal loaded, but unexpected content. Assuming inaccessible due to previous check.")
                    return []

        except httpx.RequestError as e:
            self.warn(f"Network error when accessing {PORTAL_URL}: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred: {e}")
            return []
