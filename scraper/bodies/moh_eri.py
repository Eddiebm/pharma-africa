"""
Ministry of Health Eritrea (MOH ERI)

Portal URL: https://www.moh.gov.er (This appears to be a government homepage, not a specific drug registration portal.)

Strategy:
Since no specific drug registration portal or API is publicly available at the provided URL,
and searching for common prefixes (a-z) on the homepage yields no relevant results or search functionality,
this scraper will log a warning and return an empty list.
"""

import logging
import sys
import os
import time
import json

import httpx
from bs4 import BeautifulSoup
from datetime import date

# Assuming 'base.py' and 'normalize.py' are in the parent directory or accessible via sys.path
# If not, adjust sys.path.insert accordingly.
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean


class EritreaScraper(BaseRegulatoryScraper):
    body_code = "MOH_ERI"
    country_code = "ERI"
    source_url = "https://www.moh.gov.er"

    def fetch(self) -> list[RegistrationRecord]:
        self.log(
            f"No specific drug registration portal found for {self.source_url}. "
            "The provided URL appears to be a general government homepage. "
            "Attempting to search with single letter prefixes did not yield relevant results."
        )
        self.warn(
            f"No public drug registration data found for Eritrea at {self.source_url}. Returning empty list."
        )
        return []


if __name__ == "__main__":
    # Example usage (for testing purposes)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Ensure base and normalize modules are available in the path
    # This is a common setup for such scrapers if they are in a sub-directory
    # of a larger project. Adjust as needed for your project structure.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)

    try:
        from base import BaseRegulatoryScraper, RegistrationRecord
        from normalize import parse_date, normalize_status, clean
        print("Successfully imported base and normalize modules.")
    except ImportError as e:
        print(f"Error importing base or normalize modules: {e}")
        print("Please ensure 'base.py' and 'normalize.py' are in a location accessible by sys.path.")
        sys.exit(1)

    scraper = EritreaScraper()
    records = scraper.fetch()

    if records:
        print(f"Fetched {len(records)} records:")
        for i, record in enumerate(records):
            print(f"{i+1}. {record}")
    else:
        print("No records fetched.")