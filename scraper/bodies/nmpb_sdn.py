"""
National Medicines and Poisons Board (NMPB) - Sudan
Portal URL: https://www.nmpb.gov.sd

The portal does not appear to have a direct, searchable database of registered products accessible via a public API or a clear web interface for product registration searching.
The available links under "الخدمات الالكترونية" (Electronic Services) are:
- نظام التقديم الإلكتروني (Electronic Submission System): Requires login.
- التحقق من الشهادات (Certificate Verification): Seems to be for verifying certificates, not searching products.
- المنتجات المسجلة (Registered Products): This link redirects to a page that appears to be part of the "Certificate Verification" system or a similar dashboard, not a searchable product list.

Given the lack of a discoverable public product registration search functionality, this scraper will not be able to extract registration data and will return an empty list with a warning.
"""

import logging
import httpx
from bs4 import BeautifulSoup
from datetime import date

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "SDN"
BODY_CODE = "NMPB_SDN"
PORTAL_URL = "https://www.nmpb.gov.sd"

class SudanScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to access registration data for {self.country_code} from {self.source_url}")
        self.log(f"The portal {self.source_url} does not appear to have a public, searchable product registration database.")
        self.log("The links under 'الخدمات الالكترونية' (Electronic Services) do not provide direct product search functionality.")
        self.log("Returning an empty list as no data can be scraped.")
        return []

    def _parse_html(self, html: str, source_url: str) -> list[RegistrationRecord]:
        """This method is not used as the portal has no searchable product data."""
        return []

    def _map_columns(self, headers: list[str]) -> dict[str, int]:
        """This method is not used as the portal has no searchable product data."""
        return {}