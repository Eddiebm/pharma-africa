"""
Botswana Medicines Regulatory Authority (BOMRA)
Portal: https://www.bomra.co.bw

The provided HTML indicates the website is currently under maintenance.
If the website were operational, a strategy would be implemented to
scrape the product registration data.

Current Strategy:
Given the current maintenance page, direct scraping is not possible.
If the site were live, the approach would likely involve:
1. Identifying a search form or API endpoint for product registration data.
2. If a search form exists, simulating searches with various prefixes (e.g., a-z)
   to retrieve all available records.
3. If an API exists, understanding its parameters and making paginated requests.
4. Parsing the returned HTML or JSON to extract RegistrationRecord fields.

As the site is unavailable, this scraper will return an empty list and log a warning.
"""

import logging
import httpx
from bs4 import BeautifulSoup
from datetime import date
from typing import Optional

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "BWA"
BODY_CODE = "BURS_BWA"
SOURCE_URL = "https://www.bomra.co.bw"
MAINTENANCE_MESSAGE = "The website is currently unavailable due to maintenance."


class BotswanaScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to fetch data from {SOURCE_URL}")
        records: list[RegistrationRecord] = []

        try:
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                resp = client.get(self.source_url)
                resp.raise_for_status()
                html = resp.text
                soup = BeautifulSoup(html, "lxml")

                # Check for maintenance message
                if "Maintenance" in soup.title.string or "maintenance" in html.lower():
                    self.warn(MAINTENANCE_MESSAGE)
                    return records

                # If not under maintenance, proceed with scraping logic (placeholder)
                # The current provided HTML is ONLY for maintenance.
                # If a search page were available, the logic below would be implemented:

                # Example placeholder for potential search logic:
                # If there was a search form:
                # search_url = "https://www.bomra.co.bw/search"
                # for letter in 'abcdefghijklmnopqrstuvwxyz':
                #     params = {'query': letter}
                #     page_resp = client.get(search_url, params=params)
                #     page_html = page_resp.text
                #     page_soup = BeautifulSoup(page_html, "lxml")
                #     # Parse table from page_soup and append to records
                #     # Deduplicate based on registration_no

                # If no search functionality or if maintenance persists, log and return empty.
                self.warn("No discernible product search functionality found or website is under maintenance.")

        except httpx.HTTPStatusError as e:
            self.warn(f"HTTP error occurred: {e}")
        except httpx.RequestError as e:
            self.warn(f"An error occurred while requesting {self.source_url}: {e}")
        except Exception as e:
            self.warn(f"An unexpected error occurred: {e}")

        return records
