"""
Côte d'Ivoire — AIRP (Autorité Ivoirienne de Régulation Pharmaceutique)
API: https://api.airpdigital.com/api/data/medications
Type: Laravel REST API with page/rowsPerPage pagination
Total: ~7,192 records
Fields: numero_amm, denomination, dci, laboratory_owner, country_owner,
        acquiring_date, expiry_date
"""
import logging
from datetime import date, datetime

import time
import httpx

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import normalize_status, clean

COUNTRY_CODE = "CI"
API_BASE = "https://api.airpdigital.com/api"
LIST_URL = "https://www.airpdigital.com/datapharma/liste-des-medicaments-enregistres"
PAGE_SIZE = 100
REQUEST_DELAY = 0.5   # seconds between pages
RETRY_DELAY   = 10.0  # seconds to wait after a 429

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "application/json",
    "Origin": "https://www.airpdigital.com",
    "Referer": "https://www.airpdigital.com/",
}


def _parse_ci_date(val: str | None) -> date | None:
    if not val:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _parse_row(row: dict) -> RegistrationRecord | None:
    brand    = clean(str(row.get("denomination", "") or ""))
    inn_val  = clean(str(row.get("dci", "") or ""))
    reg_no   = clean(str(row.get("numero_amm", "") or "")) or None
    holder   = clean(str(row.get("laboratory_owner", "") or "")) or None
    exp      = _parse_ci_date(str(row.get("expiry_date", "") or ""))
    acq      = _parse_ci_date(str(row.get("acquiring_date", "") or ""))

    if not inn_val and not brand:
        return None

    if exp and exp < date.today():
        status = "expired"
    else:
        status = "active"

    return RegistrationRecord(
        inn=inn_val or brand,
        brand_name=brand or None,
        country_code=COUNTRY_CODE,
        registration_no=reg_no,
        holder=holder,
        local_agent=None,
        status=status,
        expiry_date=exp,
        dosage_forms=[],
        source_url=LIST_URL,
        source_type="scrape",
        raw={
            **row,
            "acquiring_date": str(acq) if acq else None,
            "expiry_date": str(exp) if exp else None,
        },
    )


class CoteDIvoireAIRPScraper(BaseRegulatoryScraper):
    body_code = "AIRP_CI"
    country_code = COUNTRY_CODE
    source_url = LIST_URL

    def fetch(self) -> list[RegistrationRecord]:
        records: list[RegistrationRecord] = []

        with httpx.Client(
            verify=False,
            follow_redirects=True,
            timeout=30,
            headers=HEADERS,
        ) as client:
            page = 1
            total_pages = None

            while True:
                for attempt in range(4):
                    try:
                        resp = client.get(
                            f"{API_BASE}/data/medications",
                            params={
                                "page": page,
                                "rowsPerPage": PAGE_SIZE,
                                "sortBy": "id",
                                "descending": False,
                            },
                        )
                        if resp.status_code == 429:
                            wait = RETRY_DELAY * (attempt + 1)
                            self.warn(f"429 on page {page} — waiting {wait}s")
                            time.sleep(wait)
                            continue
                        resp.raise_for_status()
                        data = resp.json()
                        time.sleep(REQUEST_DELAY)
                        break
                    except Exception as e:
                        if attempt == 3:
                            self.warn(f"Page {page} failed after 4 attempts: {e}")
                            data = None
                        time.sleep(RETRY_DELAY)
                else:
                    data = None

                if not data:
                    break

                rows = data.get("data", [])
                if not rows:
                    break

                for row in rows:
                    rec = _parse_row(row)
                    if rec:
                        records.append(rec)

                if total_pages is None:
                    total_pages = data.get("last_page", 1)
                    self.log(f"Total: {data.get('total')} records across {total_pages} pages")

                if page >= total_pages:
                    break
                page += 1

        self.log(f"Total fetched: {len(records)}")
        return records
