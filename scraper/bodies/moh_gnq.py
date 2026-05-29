"""
Ministry of Health Equatorial Guinea (MOH GNQ)
Portal URL: https://www.minsabs.gov.gq
The website appears to be a government portal with no direct public drug registration search functionality.
As there is no accessible endpoint for product registration data, this scraper will return an empty list.
"""

import logging
import re
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean


class EquatorialGuineaScraper(BaseRegulatoryScraper):
    body_code = "MOH_GNQ"
    country_code = "GNQ"
    source_url = "https://www.minsabs.gov.gq"

    def fetch(self) -> list[RegistrationRecord]:
        self.log(
            "Ministry of Health Equatorial Guinea portal has no public drug registration search. "
            "Returning empty list."
        )
        return []
