"""
Guinea Direction Nationale de la Pharmacie (DNPL)

The provided HTML is for the Ministry of Health and Public Hygiene homepage (sante.gov.gn).
There is no apparent public portal or search functionality for registered pharmaceutical products
within the provided HTML or on the linked pages. The site primarily offers information about
the ministry's activities, news, and organizational structure.

Therefore, this scraper will log a warning and return an empty list as no drug registration
data can be scraped from this source.
"""

import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "GIN"
SOURCE_URL = "https://www.sante.gov.gn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}


class GuineaScraper(BaseRegulatoryScraper):
    body_code = "DNPL_GIN"
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to fetch data from {self.source_url}")

        with httpx.Client(
            headers=HEADERS, follow_redirects=True, timeout=30, verify=True
        ) as client:
            try:
                resp = client.get(self.source_url)
                resp.raise_for_status()
                html_content = resp.text

                # Check if there's any indication of a drug registry or search functionality.
                # Based on the provided HTML, this is unlikely.
                if (
                    "produits pharmaceutiques" not in html_content.lower()
                    and "enregistrement" not in html_content.lower()
                    and "liste des médicaments" not in html_content.lower()
                    and "registre" not in html_content.lower()
                ):
                    self.warn(
                        "No explicit drug registration or search functionality found on the provided portal URL. "
                        "Returning empty list."
                    )
                    return []

                # If we were to proceed with a search, we would need to find a search form
                # or a link to a dedicated drug registry page. Since none are apparent from
                # the provided HTML snippet, we will stop here.

                # Example of how one might attempt to find a search form (if it existed):
                # soup = BeautifulSoup(html_content, "lxml")
                # search_form = soup.find("form", {"id": "search-form"}) # Hypothetical ID
                # if not search_form:
                #     self.warn("No search form found. Cannot proceed.")
                #     return []

                # If a search form or link to a registry is found, implement pagination and parsing logic.
                # For this specific case, based on the provided HTML, we conclude no data is available.
                self.log("Portal structure does not suggest a public drug registration search. Returning empty list.")
                return []

            except httpx.HTTPStatusError as e:
                self.warn(f"HTTP error occurred: {e}")
                return []
            except httpx.RequestError as e:
                self.warn(f"Request error occurred: {e}")
                return []
            except Exception as e:
                self.warn(f"An unexpected error occurred: {e}")
                return []

        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv

    load_dotenv(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env"
        )
    )
    import db

    s = GuineaScraper()
    records = s.fetch()
    conn = db.get_conn()
    written = skipped = 0
    for r in records:
        w = db.upsert(conn, r)
        if w:
            written += 1
        else:
            skipped += 1
    conn.commit()
    conn.close()
    logging.info(f"OK | fetched={len(records)} written={written} skipped={skipped}")