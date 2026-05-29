"""
Pharmacy and Medicines Regulatory Board (PMRB), Sierra Leone
Portal URL: https://www.pmrb.gov.sl

Strategy:
The primary URL (https://www.pmrb.gov.sl) appears to be a government
homepage and does not provide a direct link to a public drug registration
database or search functionality. Attempts to access sub-pages or alternative
URLs did not yield a searchable product register.

Given the lack of an accessible public search portal or API, this scraper
will return an empty list and log a warning.

If a new portal or search interface becomes available, this scraper will need
to be updated to handle its specific structure, pagination, and data extraction.
"""

import logging
import sys
import os
import re
from datetime import date
from typing import Optional, List, Dict, Any

import httpx
from bs4 import BeautifulSoup

# Adjust path to import from the base module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "SLE"
BODY_CODE = "PMRB_SLE"
PORTAL_URL = "https://www.pmrb.gov.sl"
SEARCH_PREFIXES = "abcdefghijklmnopqrstuvwxyz"
PAGE_SIZE = 100

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


def _parse_html_row(row_data: Dict[str, str], source_url: str) -> Optional[RegistrationRecord]:
    """Parses a single row from the HTML table."""
    inn_val = row_data.get("inn") or ""
    brand_name = row_data.get("brand_name") or None
    reg_no = row_data.get("registration_no") or None
    holder = row_data.get("holder") or None
    expiry_raw = row_data.get("expiry_date") or ""
    status_raw = row_data.get("status") or ""
    dosage_form = row_data.get("dosage_forms") or ""

    if not inn_val and not brand_name:
        return None

    expiry_date = parse_date(expiry_raw)
    status = normalize_status(status_raw) if status_raw else (
        "expired" if (expiry_date and expiry_date < date.today()) else "active"
    )

    return RegistrationRecord(
        inn=clean(inn_val) or clean(brand_name) or "",
        brand_name=clean(brand_name),
        country_code=COUNTRY_CODE,
        registration_no=clean(reg_no),
        holder=clean(holder),
        local_agent=None,
        status=status,
        expiry_date=expiry_date,
        dosage_forms=[clean(dosage_form)] if dosage_form else [],
        source_url=source_url,
        source_type="scrape",
        raw=row_data,
    )


def _map_columns(headers: List[str]) -> Dict[str, int]:
    """Maps header names to standardized keys."""
    mapping: Dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration no", "product reg", "licence no", "license no"]):
            mapping.setdefault("registration_no", i)
        if any(x in hl for x in ["brand", "trade name", "product name", "commercial"]):
            mapping.setdefault("brand_name", i)
        if any(x in hl for x in ["inn", "generic", "active ingr", "substance", "api"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form", "presentation"]):
            mapping.setdefault("dosage_forms", i)
        if any(x in hl for x in ["company", "holder", "applicant", "manufacturer"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["expiry", "expir", "renewal", "valid"]):
            mapping.setdefault("expiry_date", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


class SierraLeoneScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> List[RegistrationRecord]:
        self.log(f"Attempting to fetch from {PORTAL_URL}")

        # The provided PORTAL_URL seems to be a government homepage, not a direct drug registry.
        # Based on current information, there is no accessible public drug search portal.
        # The fetch_error in the provided HTML snippet confirms connectivity issues or
        # that the URL does not host the expected content.
        # Therefore, returning an empty list and logging a warning.

        self.warn("No accessible public drug search portal found for Sierra Leone (PMRB).")
        self.warn("The provided URL appears to be a government homepage, not a product registry.")
        self.warn("Returning empty list. Please check for updates to the PMRB website.")

        return []
