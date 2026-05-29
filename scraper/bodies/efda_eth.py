"""
Ethiopian Food and Drug Authority (EFDA)
Portal: https://www.efda.gov.et
The portal does not appear to have a public drug registration search function.
It mainly provides information about EFDA's activities, regulations, and contact details.
Therefore, this scraper will return an empty list as no data can be scraped.
"""

import logging
import httpx
from bs4 import BeautifulSoup
from datetime import date
from typing import Optional

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "ETH"
PORTAL_URL = "https://www.efda.gov.et"
BODY_CODE = "EFDA_ETH"

class EthiopiaScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Ethiopian Food and Drug Authority (EFDA) portal does not seem to have a public drug registration search functionality.")
        self.log("Returning an empty list as no data can be scraped.")
        return []
