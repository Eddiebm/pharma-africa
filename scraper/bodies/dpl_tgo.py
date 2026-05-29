"""
Direction de la Pharmacie et du Laboratoire (DPL), Togo
Source: https://www.sante.gouv.tg

The provided HTML indicates a Cloudflare 526 error (Invalid SSL certificate).
This means the target website is currently inaccessible due to an SSL issue
with the origin server. A direct scraping attempt will fail.

The strategy here is to:
1. Log a warning that the site is inaccessible.
2. Return an empty list of records.
3. The portal does not appear to have a public drug search interface accessible
   from the given URL. It redirects to a Cloudflare error page.
"""

import logging
import sys
import os
from datetime import date
from typing import Optional

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

log = logging.getLogger("togo_dpl")

COUNTRY_CODE = "TGO"
PORTAL_URL = "https://www.sante.gouv.tg"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


def _parse_date(raw: str):
    if not raw:
        return None
    try:
        from datetime import datetime
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw[:19], fmt).date()
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _status(row: dict) -> str:
    """Map raw status to our status enum."""
    rs = (row.get("status") or "").lower()
    if "active" in rs or "valid" in rs or "en cours" in rs:
        return "active"
    if "expired" in rs or "expiré" in rs:
        return "expired"
    if "suspended" in rs or "suspendu" in rs:
        return "suspended"
    if "pending" in rs or "en attente" in rs:
        return "pending"
    if "alert" in rs or "alerte" in rs:
        return "alert"
    return "unknown"


def _to_record(row: dict, source_url: str) -> RegistrationRecord:
    """Helper to convert a raw dictionary record to a RegistrationRecord."""
    # This is a placeholder as the current URL is broken.
    # Actual parsing would depend on the structure of the drug register.
    inn = row.get("generic_name") or row.get("nom_generique") or None
    brand = row.get("brand_name") or row.get("nom_commercial") or None
    registration_no = row.get("registration_no") or row.get("numero_enregistrement") or None
    holder = row.get("holder") or row.get("titulaire") or None
    dosage_form = row.get("dosage_form") or row.get("forme_pharmaceutique") or ""
    expiry_raw = row.get("expiry_date") or row.get("date_expiration")

    # If no INN, and brand name exists, use brand name as INN.
    # If neither exists, this record might be invalid for our purpose.
    if not inn and not brand:
        raise ValueError("No INN or brand name found in record.")
    if not inn:
        inn = brand

    expiry = _parse_date(expiry_raw)

    return RegistrationRecord(
        inn=inn.strip() if inn else "",
        brand_name=brand.strip() if brand else None,
        country_code=COUNTRY_CODE,
        registration_no=registration_no.strip() if registration_no else None,
        holder=holder.strip() if holder else None,
        local_agent=None,  # Not found in sample HTML
        status=_status({"status": row.get("status") or row.get("validity")}),
        expiry_date=expiry,
        dosage_forms=[dosage_form.strip()] if dosage_form and dosage_form.strip() else [],
        source_url=source_url,
        source_type="scrape",
        raw=row,
    )


class TogoScraper(BaseRegulatoryScraper):
    body_code = "DPL_TGO"
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Attempting to fetch data from Togo DPL portal.")
        self.log(
            "The provided URL (https://www.sante.gouv.tg) is returning a Cloudflare "
            "526 error (Invalid SSL certificate). The origin server's SSL certificate "
            "is not valid or expired. This prevents direct access to the website's content."
        )
        self.warn(
            "The Togo DPL portal is inaccessible due to an SSL certificate error (526)."
            " Cannot proceed with scraping."
        )

        # Since the site is returning a 526 error, we cannot even inspect its structure
        # to determine if there's a search functionality or how to paginate.
        # Therefore, we return an empty list as no data can be fetched.
        return []
