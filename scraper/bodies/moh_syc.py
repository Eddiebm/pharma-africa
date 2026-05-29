"""
Ministry of Health Seychelles (MOH)
Portal URL: https://www.health.gov.sc/
This portal appears to be a general government website and does not contain a publicly accessible drug registration database.
Therefore, this scraper will return an empty list.
"""

import logging
import re
from datetime import date
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean


class SeychellesScraper(BaseRegulatoryScraper):
    body_code = "MOH_SYC"
    country_code = "SYC"
    source_url = "https://www.health.gov.sc/"

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Seychelles Ministry of Health portal does not appear to have a public drug registration database.")
        self.warn("Seychelles Ministry of Health portal does not appear to have a public drug registration database.")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Example usage (will return empty list)
    scraper = SeychellesScraper()
    records = scraper.fetch()
    print(f"Fetched {len(records)} records.")
