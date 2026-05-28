"""
SAHPRA — South African Health Products Regulatory Authority
Register: https://medapps.sahpra.org.za:6006
Endpoint: POST /Home/getData  (DataTables JSON API — 21,003 records)
Fields:   applicantName, licence_no, application_no, productName,
          status, expiryDate, reg_date, ingredient, therapeutic_area
Strategy: Paginate through all records via DataTables start/length params.
          No Playwright, no export guessing — direct httpx POST.
Schedule: daily
"""
import re
import sys
import os
from typing import Optional

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import clean, parse_date, normalize_status

BASE     = "https://medapps.sahpra.org.za:6006"
DATA_URL = f"{BASE}/Home/getData"
PAGE_SIZE = 500


class SAHPRAScraper(BaseRegulatoryScraper):
    body_code    = "SAHPRA"
    country_code = "ZA"
    source_url   = BASE

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Starting SAHPRA fetch via DataTables API")
        records: list[RegistrationRecord] = []
        start = 0
        total = None

        with httpx.Client(verify=False, timeout=30) as client:
            while True:
                resp = client.post(DATA_URL, data={
                    "draw":   str(start // PAGE_SIZE + 1),
                    "start":  str(start),
                    "length": str(PAGE_SIZE),
                })
                resp.raise_for_status()
                payload = resp.json()

                if total is None:
                    total = payload.get("recordsTotal", 0)
                    self.log(f"Total records: {total}")

                rows = payload.get("data", [])
                if not rows:
                    break

                for row in rows:
                    r = self._normalize(row)
                    if r:
                        records.append(r)

                start += PAGE_SIZE
                if start >= total:
                    break

        self.log(f"Fetched {len(records)} records")
        return records

    def _normalize(self, row: dict) -> Optional[RegistrationRecord]:
        brand  = clean(row.get("productName"))
        reg_no = clean(row.get("licence_no"))
        holder = clean(row.get("applicantName"))

        if not brand and not reg_no:
            return None

        inn = self._extract_inn(row.get("ingredient") or "")

        return RegistrationRecord(
            inn=inn,
            brand_name=brand,
            country_code=self.country_code,
            registration_no=reg_no,
            holder=holder,
            local_agent=None,
            status=normalize_status(clean(row.get("status"))),
            expiry_date=parse_date(row.get("expiryDate")),
            dosage_forms=[],
            source_url=self.source_url,
            source_type="scrape",
            raw=row,
        )

    @staticmethod
    def _extract_inn(ingredient: str) -> str:
        """
        Extract INN from full composition string.
        e.g. "EACH TABLET CONTAINS METFORMIN HYDROCHLORIDE 500,0 mg" → "metformin hydrochloride"
        """
        if not ingredient:
            return ""
        # Text after CONTAINS up to the first digit (strength)
        m = re.search(r"CONTAINS\s+([A-Z][A-Z\s,\(\)/]+?)(?=\s+\d)", ingredient.upper())
        if m:
            return m.group(1).strip().lower()
        # Fallback: return everything after CONTAINS
        m2 = re.search(r"CONTAINS\s+(.+)", ingredient, re.IGNORECASE)
        if m2:
            return m2.group(1).strip().lower()[:100]
        return ingredient.strip().lower()[:100]
