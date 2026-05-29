"""
Republic of Congo Direction de la Pharmacie et du Médicament (DPML)
Portal: https://www.sante.gouv.cg/
The website appears to be a standard WordPress site with no readily apparent public drug registration search functionality.
Therefore, this scraper will return an empty list.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "COG"
PORTAL_URL = "https://www.sante.gouv.cg/"
BODY_CODE = "DPML_COG"

class RepublicofCongoScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Attempting to find drug registration data on the DPML website.")
        self.log("The website structure does not appear to expose a public drug registration search.")
        self.log("Returning an empty list as no data can be scraped.")
        return []
