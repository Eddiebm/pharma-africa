"""
Ministry of Health Guinea-Bissau (MOH)
Portal: https://www.minsau.gw

Strategy:
The provided portal URL 'https://www.minsau.gw' appears to be a general government portal
and does not seem to host a dedicated, publicly accessible drug registration database
that can be scraped directly. The FETCH_ERROR indicates that the hostname itself might be
unresolvable or inaccessible in the current environment, suggesting a potential issue
with the domain or network configuration for accessing it.

Given this, a direct scraping approach is not feasible. The scraper will log a warning
and return an empty list, indicating that no drug registration data could be retrieved
from the specified portal. Future efforts would require identifying a specific,
scrapable drug registration portal or API for Guinea-Bissau.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "GNB"
PORTAL_URL = "https://www.minsau.gw"
BODY_CODE = "MOH_GNB"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng/*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
}


class GuineaBissauScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(
            "The portal 'https://www.minsau.gw' does not appear to host a publicly "
            "accessible drug registration database that can be scraped. "
            "Returning empty list."
        )
        # In a real scenario, you might attempt to connect to the URL to confirm
        # the absence of data or to try and find a hidden API.
        # For this specific case, we are informed by the problem description that
        # it's a government homepage and FETCH_ERROR is present.
        return []
