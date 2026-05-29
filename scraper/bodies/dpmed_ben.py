"""
Direction de la Pharmacie et du Médicament (DPMED) Benin
The provided HTML is for the Ministry of Health homepage (sante.gouv.bj).
There is no apparent public drug registration search or accessible API.
The website structure suggests a CMS (likely WordPress or similar) but
no specific section for drug registration lookup is visible.

Strategy:
Since no specific drug registration portal or search functionality is found,
this scraper will log a warning and return an empty list.
"""

import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "BEN"
BASE_URL = "https://sante.gouv.bj/"

class BeninScraper(BaseRegulatoryScraper):
    body_code = "DPMED_BEN"
    country_code = COUNTRY_CODE
    source_url = BASE_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("No public drug registration search found on Benin's Ministry of Health portal.")
        self.warn("Could not find a specific portal or API for drug registration data.")
        return []
