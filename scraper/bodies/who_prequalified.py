"""
WHO Prequalification scraper
Downloads FPP and API CSVs from extranet.who.int/prequal
body_code: WHO_PQ | country_code: WW (worldwide)
"""

import csv
import io
import logging
import re
import sys
import os
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseRegulatoryScraper, RegistrationRecord
import db

log = logging.getLogger("who_prequalified")

BASE_URL = "https://extranet.who.int/prequal"
FPP_CSV  = f"{BASE_URL}/medicines/prequalified/finished-pharmaceutical-products/export"
API_CSV  = f"{BASE_URL}/medicines/prequalified/active-pharmaceutical-ingredients/export"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/csv,*/*",
}


def _parse_date(raw: str):
    """Parse WHO date strings like '5 Sep, 2017' or '2023-04-12'"""
    if not raw:
        return None
    raw = raw.strip()
    from datetime import datetime
    for fmt in ("%d %b, %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _extract_inn(combined: str) -> str:
    """From 'Zidovudine Tablet 300mg', return 'Zidovudine'."""
    if not combined:
        return combined
    parts = re.split(r'\s+(?:Tablet|Capsule|Solution|Injection|Syrup|Cream|Gel|Powder|Granule|Patch|Drops|Suppository|Suspension|Concentrate)\b', combined, flags=re.I, maxsplit=1)
    return parts[0].strip() if parts else combined.strip()


def _fetch_csv(url: str, label: str) -> list[dict]:
    log.info(f"Downloading {label} CSV…")
    r = httpx.get(url, headers=HEADERS, timeout=60, follow_redirects=True)
    r.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r.text)))
    log.info(f"{label}: {len(rows)} rows fetched")
    return rows


def _fpp_to_record(row: dict) -> RegistrationRecord:
    ref = row.get("WHO Reference Number", "").strip()
    inn_raw = row.get("INN, Dosage Form and Strength", "").strip()
    inn = _extract_inn(inn_raw)
    brand_name = inn_raw if inn_raw != inn else None  # store full description as brand
    dosage_form = row.get("Dosage Form", "").strip()
    holder = row.get("Applicant", "").strip()
    pq_date_raw = row.get("Date of Prequalification", "").strip()
    therapeutic_area = row.get("Therapeutic Area", "").strip()

    return RegistrationRecord(
        inn=inn or inn_raw,
        brand_name=brand_name,
        country_code="WW",
        registration_no=ref or None,
        holder=holder or None,
        local_agent=None,
        status="active",
        expiry_date=None,
        dosage_forms=[dosage_form] if dosage_form else [],
        source_url=FPP_CSV,
        source_type="scrape",
        raw={
            "therapeutic_area": therapeutic_area,
            "pq_date": pq_date_raw,
            "product_type": row.get("Product Type", ""),
            "basis": row.get("Basis of Listing", ""),
        },
    )


def _api_to_record(row: dict) -> RegistrationRecord:
    ref = row.get("WHO Product ID", "").strip()
    inn = row.get("INN", "").strip()
    holder = row.get("Applicant organization", "").strip()
    pq_date_raw = row.get("Date of prequalification", "").strip()
    grade = row.get("Grade", "").strip()
    therapeutic_area = row.get("Therapeutic area", "").strip()

    return RegistrationRecord(
        inn=inn,
        brand_name=None,
        country_code="WW",
        registration_no=ref or None,
        holder=holder or None,
        local_agent=None,
        status="active",
        expiry_date=None,
        dosage_forms=[],
        source_url=API_CSV,
        source_type="scrape",
        raw={
            "therapeutic_area": therapeutic_area,
            "pq_date": pq_date_raw,
            "grade": grade,
            "product_type": "Active Pharmaceutical Ingredient",
        },
    )


class WHOPrequalifiedScraper(BaseRegulatoryScraper):
    body_code = "WHO_PQ"
    country_code = "WW"
    source_url = BASE_URL

    def fetch(self) -> list[RegistrationRecord]:
        records = []

        fpp_rows = _fetch_csv(FPP_CSV, "FPP")
        for row in fpp_rows:
            try:
                records.append(_fpp_to_record(row))
            except Exception as e:
                log.warning(f"FPP row error: {e} | {row}")

        api_rows = _fetch_csv(API_CSV, "API")
        for row in api_rows:
            try:
                records.append(_api_to_record(row))
            except Exception as e:
                log.warning(f"API row error: {e} | {row}")

        return records


def run(dry_run: bool = False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = WHOPrequalifiedScraper()

    records = scraper.fetch()
    log.info(f"Total fetched: {len(records)}")

    if dry_run:
        log.info("Dry-run — not writing to DB")
        return

    conn = db.get_conn()
    try:
        written = skipped = 0
        for rec in records:
            if db.upsert(conn, rec):
                written += 1
            else:
                skipped += 1
        conn.commit()
        log.info(f"OK | fetched={len(records)} written={written} skipped={skipped}")
    finally:
        conn.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    run(dry_run=dry)
