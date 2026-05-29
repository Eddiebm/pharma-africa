"""
ARFA — Agência de Regulação e Supervisão dos Fármaco (Cape Verde)
Portal: https://www.arfa.gov.cv
This portal appears to be a government homepage without a public drug search functionality.
Therefore, it's not possible to scrape registration records.
"""

import logging
import re
import sys
import os
from datetime import date
from typing import Optional, List, Dict

import httpx
from bs4 import BeautifulSoup

# Adjust path to import from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "CPV"
BODY_CODE = "ARFA_CPV"
PORTAL_URL = "https://www.arfa.gov.cv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _map_columns(headers: list[str]) -> dict[str, int]:
    """Maps table headers to RegistrationRecord fields."""
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["registro", "número de registro", "registration number"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["nome comercial", "marca", "nome do produto", "trade name", "brand name"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["princípio ativo", "nome genérico", "inn", "generic name"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["forma farmacêutica", "dosagem", "dosage form"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["titular", "detentor", "empresa", "holder", "company", "applicant"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["agente local", "representante", "local agent"]):
            mapping.setdefault("local_agent", i)
        if any(x in hl for x in ["data de validade", "validade", "expir", "expiry", "renewal"]):
            mapping.setdefault("expiry", i)
        if "status" in hl or "estado" in hl:
            mapping.setdefault("status", i)
    return mapping


def _parse_html_table(html: str, source_url: str) -> list[RegistrationRecord]:
    """Parses a single HTML table into RegistrationRecord objects."""
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return records

    rows = table.find_all("tr")
    if len(rows) < 2:  # Need at least header and one data row
        return records

    headers = [clean(th.get_text()) for th in rows[0].find_all(["th", "td"])]
    col_map = _map_columns(headers)

    if not col_map:
        logging.warning(f"[ARFA_CPV] Could not map columns from headers: {headers}")
        return records

    for row in rows[1:]:
        cells = [clean(td.get_text()) for td in row.find_all("td")]
        if not cells or len(cells) < 2:
            continue

        def get(key: str) -> str:
            idx = col_map.get(key)
            return cells[idx] if idx is not None and idx < len(cells) else ""

        reg_no = get("reg_no") or None
        trade_name = get("trade_name") or None
        inn_val = get("inn") or ""
        dosage_form = get("dosage_form") or ""
        holder = get("holder") or None
        local_agent = get("local_agent") or None
        expiry_raw = get("expiry") or None
        status_raw = get("status") or ""

        # Skip if no identifiable product name or INN
        if not inn_val and not trade_name:
            continue

        expiry_date = parse_date(expiry_raw)
        status = normalize_status(status_raw) if status_raw else (
            "expired" if expiry_date and expiry_date < date.today() else "active"
        )

        records.append(RegistrationRecord(
            inn=inn_val or trade_name,  # Fallback to brand name if INN is missing
            brand_name=trade_name,
            country_code=COUNTRY_CODE,
            registration_no=reg_no,
            holder=holder,
            local_agent=local_agent,
            status=status,
            expiry_date=expiry_date,
            dosage_forms=[dosage_form] if dosage_form else [],
            source_url=source_url,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    return records


class CapeVerdeScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to fetch from {self.source_url}")
        records: list[RegistrationRecord] = []

        # Based on the provided HTML snippet (FETCH_ERROR), the portal might not be
        # accessible or does not host a searchable drug register.
        # The examples show patterns for XCRUD, DataTables, or simple HTML tables.
        # If the portal only serves a homepage without a search or registry,
        # we cannot proceed.

        try:
            with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
                response = client.get(self.source_url)
                response.raise_for_status()
                html_content = response.text

                # Check if the response indicates a search function or a data table
                soup = BeautifulSoup(html_content, "lxml")

                # Heuristic check: Look for elements that might suggest a searchable register.
                # This is a guess, as the provided HTML snippet is just an error.
                # If specific form elements or tables related to drug registration
                # are found, the parsing logic would go here.
                # For example, searching for common pagination elements like 'next', 'previous',
                # or tables with headers like 'Registration Number', 'Product Name', etc.

                # In this specific case, the error "FETCH_ERROR: [Errno 8] nodename nor servname provided, or not known"
                # suggests a network or DNS issue with the portal URL itself.
                # If the URL is valid but leads to a static page without a search:
                # A more robust check would involve looking for input fields for search,
                # or specific table structures that usually hold product data.

                # Since the initial fetch failed with a DNS/name resolution error,
                # or if the URL resolves but leads to a homepage with no search:
                logging.warning(
                    f"[{self.body_code}] The portal at {self.source_url} appears to be inaccessible "
                    f"or does not provide a public drug registration search interface. "
                    f"No records can be scraped."
                )
                return []

        except httpx.ConnectError as e:
            logging.error(f"[{self.body_code}] Connection error to {self.source_url}: {e}")
            self.log("Portal is inaccessible or URL is incorrect.")
            return []
        except httpx.HTTPStatusError as e:
            logging.error(f"[{self.body_code}] HTTP error accessing {self.source_url}: {e}")
            self.log("Received an error status code from the portal.")
            return []
        except Exception as e:
            logging.error(f"[{self.body_code}] An unexpected error occurred: {e}")
            self.log("An unexpected error occurred during fetching.")
            return []

        # If the portal were to have a searchable interface, the logic would look like this:
        # try:
        #     # Example: Iterate through letters 'a' to 'z' to search for products
        #     for char_code in range(ord('a'), ord('z') + 1):
        #         prefix = chr(char_code)
        #         self.log(f"Searching for products starting with '{prefix}'...")
        #         # Construct search query parameters based on portal's form/API
        #         search_params = {
        #             "search_field": "product_name", # Example field
        #             "search_value": prefix,
        #             "page": "1" # Start with the first page
        #         }
        #         # Loop through pagination if necessary
        #         page_num = 1
        #         while True:
        #             search_params["page"] = str(page_num)
        #             response = client.get(self.source_url, params=search_params)
        #             response.raise_for_status()
        #             html_content = response.text
        #             page_records = _parse_html_table(html_content, f"{self.source_url}?page={page_num}&search={prefix}")
        #
        #             if not page_records:
        #                 break # No more records for this prefix or page
        #
        #             # De-duplication logic could be added here if needed, though the example
        #             # scrapers often rely on unique IDs or a set to track seen records.
        #             # For simplicity, we assume _parse_html_table might return duplicates
        #             # if the backend doesn't handle it well, and rely on a final de-duplication.
        #             records.extend(page_records)
        #
        #             # Pagination logic: Check for a 'next' button or if current page is last
        #             # This part is highly portal-specific and requires inspecting the HTML structure.
        #             # For example:
        #             # soup = BeautifulSoup(html_content, "lxml")
        #             # if not soup.find("a", class_="next-page"):
        #             #    break
        #
        #             page_num += 1
        #             self.log(f"Fetched page {page_num} for prefix '{prefix}'")
        #             # Add a small delay to avoid overwhelming the server
        #             # time.sleep(0.5)
        #
        # except Exception as e:
        #     self.warn(f"Error during search and pagination for prefix '{prefix}': {e}")
        #
        # # Final de-duplication based on registration number if necessary
        # unique_records = {}
        # for rec in records:
        #     if rec.registration_no:
        #         unique_records[rec.registration_no] = rec
        #     else:
        #         # Handle records without registration numbers if they are important
        #         # For now, we prioritize records with registration numbers for deduplication
        #         pass
        #
        # final_records = list(unique_records.values())
        # self.log(f"Total records fetched after de-duplication: {len(final_records)}")
        # return final_records

        self.log(f"No specific scraping logic implemented for {self.source_url} as it appears to lack a search interface.")
        return []
