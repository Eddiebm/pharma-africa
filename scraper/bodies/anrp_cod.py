"""
Autorité Nationale de Réglementation Pharma (ANRP) - Democratic Republic of Congo
The provided HTML is from the Ministry of Public Health website (sante.gouv.cd),
which appears to be a general government portal rather than a dedicated drug
registration search portal. There is no visible search functionality for
pharmaceutical products. Therefore, this scraper will return an empty list.
"""

import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "COD"
BODY_CODE = "ANRP_COD"
PORTAL_URL = "https://www.sante.gouv.cd"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


class DRCScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(
            "ANRP portal (sante.gouv.cd) does not appear to have a public drug registration search interface. "
            "Returning empty list."
        )
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = DRCScraper()
    records = scraper.fetch()
    print(f"Fetched {len(records)} records.")