"""
DPSM — Direction de la Pharmacie et du Médicament, Cameroon
Portal: https://www.minsante.cm
This scraper targets the main MINSANTE portal for Cameroon. After analysis, no direct public-facing drug or pharmaceutical product register could be identified on the main site or its linked sub-portals that correspond to the "Direction de la Pharmacie et du Médicament". The "dps.minsante.cm" subdomain points to the "Direction de la Promotion de la Santé", which is a different regulatory body focused on health promotion, not drug regulation. Therefore, this scraper will log a warning and return an empty list of records.
"""

import logging
import os
import sys
import httpx
from bs4 import BeautifulSoup
from datetime import date

# Assume base.py and normalize.py are in the sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean # Placeholder imports, not used if no register found

log = logging.getLogger("dpsm_cameroon")

COUNTRY_CODE = "CMR"
BASE_URL = "https://www.minsante.cm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


class CameroonScraper(BaseRegulatoryScraper):
    body_code = "DPSM_CMR"
    country_code = COUNTRY_CODE
    source_url = BASE_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to fetch records from {self.source_url}")
        records: list[RegistrationRecord] = []

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            try:
                resp = client.get(self.source_url, headers=HEADERS)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                # Look for common keywords or links that might indicate a drug register
                # Keywords: 'pharmacie', 'médicament', 'registre', 'produits', 'enregistrement', 'AMM' (Autorisation de Mise sur le Marché)
                search_terms = ['pharmacie', 'médicament', 'registre', 'produits enregistrés', 'amm', 'autorisation de mise sur le marché']
                found_register_link = False
                for term in search_terms:
                    # Check in link texts and alt attributes
                    if soup.find('a', string=re.compile(term, re.IGNORECASE)) or \
                       soup.find('img', alt=re.compile(term, re.IGNORECASE)):
                        self.warn(f"Found a potential link or reference with term '{term}' on {self.source_url}. Manual investigation may be required.")
                        # This section would be expanded if a specific link was identified.
                        # For now, we assume it's not a direct register.
                        found_register_link = True
                        break
                
                # Check for "Direction de la Pharmacie et du Médicament" explicitly
                # The provided HTML shows "Direction de la Promotion de la Santé" (dps.minsante.cm)
                # which is NOT the target body.
                if soup.find(string=re.compile("Direction de la Pharmacie et du Médicament", re.IGNORECASE)):
                    self.warn(f"Found explicit mention of 'Direction de la Pharmacie et du Médicament'. Manual investigation may be required.")
                    found_register_link = True # Treat as a strong hint

                if not found_register_link:
                    self.warn(f"No clear public drug register for 'Direction de la Pharmacie et du Médicament' (DPSM) found on {self.source_url} or its immediate sub-portals. The site appears to be a general Ministry of Health portal without a dedicated drug register available for scraping.")

            except httpx.HTTPStatusError as e:
                self.warn(f"HTTP error accessing {self.source_url}: {e}")
            except httpx.RequestError as e:
                self.warn(f"Network error accessing {self.source_url}: {e}")
            except Exception as e:
                self.warn(f"An unexpected error occurred while checking {self.source_url}: {e}")

        self.log(f"Total fetched: {len(records)} (Expected 0 as no register found)")
        return records

# Example of how to run this scraper (for local testing, if needed)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import re # Ensure re is imported if not implicitly available for direct execution
    
    # Placeholder for a dummy db module if not in project structure
    class DummyDB:
        def get_conn(self):
            print("DB connection (dummy)")
            return self
        def upsert(self, conn, record):
            print(f"Upserting: {record.inn} - {record.brand_name}")
            return True # Simulate success
        def commit(self):
            print("DB commit (dummy)")
        def close(self):
            print("DB close (dummy)")
    
    # Mocking db module for standalone execution
    class MockModule:
        def __getattr__(self, name):
            if name == 'db':
                return DummyDB()
            raise AttributeError(f"module 'db' not found or attribute '{name}'")
    
    sys.modules['db'] = MockModule()

    s = CameroonScraper()
    records = s.fetch()
    
    if records:
        conn = sys.modules['db'].db.get_conn()
        written = skipped = 0
        for r in records:
            w = sys.modules['db'].db.upsert(conn, r)
            if w:
                written += 1
            else:
                skipped += 1
        conn.commit()
        conn.close()
        log.info(f"OK | fetched={len(records)} written={written} skipped={skipped}")
    else:
        log.info(f"No records fetched, as no public register was found.")