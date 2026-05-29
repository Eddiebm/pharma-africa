"""
Central African Republic - Direction de la Pharmacie et du Médicament (DPM)
Portal URL: https://www.sante.gouv.cf/

This portal does not appear to have a dedicated section for searching registered medicines.
The provided HTML snippet is for the main government ministry homepage.
Without a specific drug registration search interface or an accessible API,
it's not possible to scrape registration data.

Therefore, this scraper will return an empty list.
"""

import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "CAF"
PORTAL_URL = "https://www.sante.gouv.cf/"

class CentralAfricanRepublicScraper(BaseRegulatoryScraper):
    body_code = "DPM_CAF"
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        """
        Attempts to fetch drug registration records from the Central African Republic's
        Ministry of Health portal.

        Since the portal does not seem to offer a public drug registration search,
        this method will log a warning and return an empty list.
        """
        self.log(
            "The Central African Republic's Ministry of Health portal "
            "(https://www.sante.gouv.cf/) does not appear to have a public interface "
            "for searching registered medicines. Returning empty list."
        )
        # As there's no discernible way to access drug registration data through the
        # provided portal, we return an empty list and log the reason.
        return []

if __name__ == "__main__":
    # This block is for local testing and demonstration purposes.
    # It requires the 'dotenv' and 'db' modules to be available.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import os
    import sys
    from dotenv import load_dotenv

    # Adjust path to find base modules if running from a different directory
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env"))
        import db
    except ImportError:
        db = None
        logging.warning("Skipping DB insertion: 'dotenv' or 'db' module not found.")

    s = CentralAfricanRepublicScraper()
    records = s.fetch()

    if db:
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
    else:
        logging.info(f"OK | fetched={len(records)} (no DB insertion)")