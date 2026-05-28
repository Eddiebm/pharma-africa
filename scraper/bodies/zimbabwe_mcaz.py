"""
Zimbabwe MCAZ (Medicines Control Authority of Zimbabwe)
API: https://onlineservices.mcaz.co.zw/onlineregister/Medicines/GetMedicinesByCategory
Kendo Grid DataSource with aspnetmvc-ajax transport.
Category 1 = Human Prescription/OTC medicines (~3,060 records)
Category 2 = Veterinary medicines (~381 records)
Category 3 = Complementary/Traditional medicines (~465 records)
"""

import logging
import sys
import os
import time
from datetime import datetime

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseRegulatoryScraper, RegistrationRecord
import db

log = logging.getLogger("zimbabwe_mcaz")

BASE = "https://onlineservices.mcaz.co.zw/onlineregister"
CATEGORIES = [1, 2, 3]   # 0 and 5 return empty
PAGE_SIZE = 100
REQUEST_DELAY = 0.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": f"{BASE}/medicines",
}


def _parse_date(raw: str):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _fetch_category(client: httpx.Client, category: int) -> list[dict]:
    """Fetch all records for a given category, handling Kendo pagination."""
    skip = 0
    all_rows = []

    while True:
        params = {
            "category": category,
            "take": PAGE_SIZE,
            "skip": skip,
            "page": (skip // PAGE_SIZE) + 1,
            "pageSize": PAGE_SIZE,
        }
        try:
            r = client.get(
                f"{BASE}/Medicines/GetMedicinesByCategory",
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning(f"Category {category} page {params['page']} failed: {e}")
            break

        rows = data.get("Data", [])
        total = data.get("Total", 0)

        if not rows:
            break

        all_rows.extend(rows)
        log.info(f"  Category {category}: fetched {len(all_rows)}/{total}")

        if len(all_rows) >= total:
            break

        skip += PAGE_SIZE
        time.sleep(REQUEST_DELAY)

    return all_rows


def _row_to_record(row: dict) -> RegistrationRecord:
    inn = (row.get("Generic_Name") or "").strip()
    brand_name = (row.get("Trade_Name") or "").strip() or None
    reg_no = (row.get("Registration_No") or "").strip() or None
    holder = (row.get("ApplicantName") or row.get("PrincipalName") or "").strip() or None
    dosage_form = (row.get("Forms") or "").strip()
    strength = (row.get("Strength") or "").strip()
    expiry_raw = row.get("Expiry_Date") or ""
    date_reg_raw = row.get("Date_Registered") or ""
    category = (row.get("Category") or "").strip()

    expiry_date = _parse_date(expiry_raw)
    status = "active" if expiry_date and expiry_date.year > 2026 else "expired"
    # If no expiry, treat as active (registration may not expire)
    if not expiry_date:
        status = "active"

    return RegistrationRecord(
        inn=inn or (brand_name or "unknown"),
        brand_name=brand_name,
        country_code="ZW",
        registration_no=reg_no,
        holder=holder,
        local_agent=None,
        status=status,
        expiry_date=expiry_date,
        dosage_forms=[dosage_form] if dosage_form else [],
        source_url=f"{BASE}/medicines",
        source_type="scrape",
        raw={
            "strength": strength,
            "category": category,
            "manufacturers": row.get("Manufacturers", ""),
            "date_registered": date_reg_raw,
        },
    )


class ZimbabweMCAZScraper(BaseRegulatoryScraper):
    body_code = "MCAZ_ZW"
    country_code = "ZW"
    source_url = f"{BASE}/medicines"

    def fetch(self) -> list[RegistrationRecord]:
        records = []
        with httpx.Client(follow_redirects=True) as client:
            for cat in CATEGORIES:
                log.info(f"Fetching category {cat}…")
                rows = _fetch_category(client, cat)
                seen_reg_nos = set()
                for row in rows:
                    try:
                        rec = _row_to_record(row)
                        # Dedup by reg_no (cat 3 and 4 overlap)
                        key = rec.registration_no or rec.inn
                        if key in seen_reg_nos:
                            continue
                        seen_reg_nos.add(key)
                        records.append(rec)
                    except Exception as e:
                        log.warning(f"Row error: {e}")

        log.info(f"Total fetched: {len(records)}")
        return records


def run(dry_run: bool = False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = ZimbabweMCAZScraper()
    records = scraper.fetch()

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
    run(dry_run="--dry-run" in sys.argv)
