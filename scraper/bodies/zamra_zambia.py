"""
ZAMRA — Zambia Medicines Regulatory Authority
API: https://app.zamra.co.zm:42882/portal/publicaccess/onSearchPublicRegisteredproducts
DevExtreme DataGrid with skip/take pagination. Total ~4,600 records.
"""

import logging
import sys
import os
import time
import json

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseRegulatoryScraper, RegistrationRecord

log = logging.getLogger("zamra_zambia")

BASE_URL = "https://app.zamra.co.zm:42882/portal"
PAGE_SIZE = 100
REQUEST_DELAY = 0.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*; q=0.9",
    "Referer": "https://app.zamra.co.zm:42882/portal",
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
    """Map ZAMRA validity status to our status enum."""
    rs = (row.get("registration_status") or "").lower()
    vs = (row.get("validity_status") or "").lower()
    if "registered" in rs and "compliant" in rs:
        return "active"
    if "expired" in rs or "expired" in vs:
        return "expired"
    if "cancelled" in rs or "suspended" in rs or "revoked" in rs:
        return "cancelled"
    return "active"


def _to_record(row: dict) -> RegistrationRecord:
    inn = (row.get("generic_name") or "").strip() or None
    brand = (row.get("brand_name") or "").strip() or None
    # inn is NOT NULL in DB — fall back to brand_name, then skip via ValueError
    if not inn:
        if not brand:
            raise ValueError("no INN or brand name")
        inn = brand
    cert_no = (row.get("certificate_no") or "").strip() or None
    holder = (row.get("registrant") or "").strip() or None
    dosage_form = (row.get("dosage_form") or "").strip()
    expiry_raw = row.get("app_expiry_Date") or row.get("expiry_date")
    expiry = _parse_date(expiry_raw)

    return RegistrationRecord(
        country_code="ZM",
        inn=inn,
        brand_name=brand,
        registration_no=cert_no,
        holder=holder,
        local_agent=None,
        status=_status(row),
        expiry_date=expiry,
        dosage_forms=[dosage_form] if dosage_form else [],
    )


class ZAMRAZambiaScraper(BaseRegulatoryScraper):
    body_code = "ZAMRA_ZM"

    def fetch(self) -> list[RegistrationRecord]:
        records = []
        seen_ids: set[int] = set()

        with httpx.Client(headers=HEADERS, verify=False, timeout=30) as client:
            skip = 0
            total = None

            while True:
                params = {
                    "skip": skip,
                    "take": PAGE_SIZE,
                    "section_id": "",
                    "sub_modulesin": "",
                    "extra_paramsdata": "{}",
                }
                try:
                    resp = client.get(
                        f"{BASE_URL}/publicaccess/onSearchPublicRegisteredproducts",
                        params=params,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    log.warning(f"ZAMRA request failed at skip={skip}: {e}")
                    break

                if total is None:
                    total = data.get("totalCount", 0)
                    log.info(f"ZAMRA total: {total} records")

                rows = data.get("data") or []
                if not rows:
                    break

                for row in rows:
                    pid = row.get("product_id")
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    try:
                        records.append(_to_record(row))
                    except Exception as e:
                        log.warning(f"Skipping row {pid}: {e}")

                skip += len(rows)
                log.info(f"ZAMRA: fetched {skip}/{total}")

                if total and skip >= total:
                    break
                time.sleep(REQUEST_DELAY)

        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env"))
    import db
    s = ZAMRAZambiaScraper()
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
    log.info(f"OK | fetched={len(records)} written={written} skipped={skipped}")
