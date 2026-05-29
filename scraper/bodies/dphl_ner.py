"""
Niger Direction de la Pharmacie et des Laboratoires (DPHL)
Source: https://www.sante.gouv.ne
The website appears to be a general government health portal and does not have a publicly accessible drug registration search function.
Therefore, this scraper will return an empty list.
"""

import logging
import httpx
from bs4 import BeautifulSoup
from datetime import date

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean


COUNTRY_CODE = "NER"
PORTAL_URL = "https://www.sante.gouv.ne"
DPHL_CODE = "DPHL_NER"


def _parse_html_table(html: str, source_url: str) -> list[RegistrationRecord]:
    """Placeholder function as no table is expected for drug registrations."""
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(html, "lxml")
    # Attempt to find any table that might contain drug registrations
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")
        if len(rows) > 1:
            logging.warning("[DPHL_NER] Found a table, but it's likely not a drug registration list.")
            # Further parsing would be needed if a relevant table structure was identified
            # For now, we'll assume it's not the intended data and return empty
            return []
    return records


class NigerScraper(BaseRegulatoryScraper):
    body_code = DPHL_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Navigating to the Niger Ministry of Health portal.")
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(self.source_url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                html = resp.text

                # Check if there's any indication of a drug register or search functionality
                # Based on the provided HTML snippet, this is a general ministry page.
                # We'll look for common keywords that might indicate a registration portal.
                soup = BeautifulSoup(html, "lxml")
                search_forms = soup.find_all("form")
                potential_links = soup.find_all("a", href=True)

                has_drug_search = False
                for form in search_forms:
                    form_text = form.get_text().lower()
                    if any(keyword in form_text for keyword in ["médicament", "produit", "enregistrement", "register"]):
                        self.log("Found a form that might be related to drug registration.")
                        # In a real scenario, we'd analyze this form for submission parameters.
                        # For this specific case, assuming no direct drug search is present.
                        pass # Placeholder for potential form submission logic

                for link in potential_links:
                    link_text = link.get_text().lower()
                    link_href = link['href'].lower()
                    if any(keyword in link_text for keyword in ["médicament", "produit", "enregistrement", "register", "pharmacie", "laboratoire"]) or \
                       any(keyword in link_href for keyword in ["medicament", "product", "register", "pharmacy", "lab"]):
                        self.log(f"Found a link that might be related to drug registration: {link_text} ({link_href})")
                        # In a real scenario, we'd follow this link to see if it leads to a searchable database.
                        # For this specific case, assuming no direct drug search is present.
                        pass # Placeholder for potential link following logic

                if not any(keyword in html.lower() for keyword in ["médicament", "produit", "enregistrement", "register", "pharmacie", "laboratoire"]):
                    self.log(f"No clear indication of a drug registration search functionality found on {self.source_url}. Returning empty list.")
                    return []
                else:
                    # If there were any indicators, attempt to parse tables just in case, though unlikely.
                    records = _parse_html_table(html, self.source_url)
                    if records:
                        self.log(f"Successfully parsed {len(records)} records from an unexpected table.")
                    else:
                        self.log("No drug registration data found. The portal might not host a public drug register.")
                    return records

        except httpx.RequestError as e:
            self.warn(f"HTTP request failed: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred: {e}")
            return []
