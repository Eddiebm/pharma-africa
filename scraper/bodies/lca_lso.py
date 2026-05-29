"""
Lesotho Commodities Agency (LCA)
Source: Ministry of Health website (https://health.gov.ls)
The provided HTML indicates a WordPress site with Elementor and Download Manager plugins.
There is no direct public drug registration search portal visible in the provided HTML.
The website appears to be a general ministry website, not a dedicated regulatory portal for product registration.
Therefore, this scraper will return an empty list and log a warning.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "LSO"
PORTAL_URL = "https://health.gov.ls"

# The provided HTML does not show a direct drug registration search.
# It's a general Ministry of Health website.

class LesothoScraper(BaseRegulatoryScraper):
    body_code = "LCA_LSO"
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Lesotho Ministry of Health website does not appear to have a public drug registration portal.")
        self.log("Returning an empty list.")
        return []
