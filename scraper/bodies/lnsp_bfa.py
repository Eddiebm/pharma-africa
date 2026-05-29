"""
Laboratoire National de Santé Publique (LNSP), Burkina Faso
Source: https://www.sante.gov.bf/
This is the main government health ministry website and does not appear to have a public drug registration search.
It only contains general news and information. Therefore, no drug registration data can be scraped.
"""

import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "BFA"
REGULATORY_BODY_URL = "https://www.sante.gov.bf/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}

class BurkinaFasoScraper(BaseRegulatoryScraper):
    body_code = "LNSP_BFA"
    country_code = COUNTRY_CODE
    source_url = REGULATORY_BODY_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Attempting to scrape Burkina Faso Ministry of Health website.")
        self.log("This website does not appear to have a public drug registration search portal.")
        self.log("Returning an empty list as no searchable data is available.")
        return []
