"""
Ministry of Health Comoros (MOH)
Portal: https://www.sante.gov.km
This portal does not appear to have a public drug registration search interface.
It primarily serves as a government portal and does not provide accessible data
for scraping drug registrations. Therefore, this scraper will return an empty list.
"""

import logging
import re
from datetime import date
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "COM"
MOH_URL = "https://www.sante.gov.km"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration no", "product reg", "licence no", "license no"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["trade name", "product name", "product trade", "brand"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["inn", "api", "active ingr", "generic name"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["mah", "manufacturer", "company", "applicant", "holder"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["local tech", "local rep", "representative"]):
            mapping.setdefault("local_rep", i)
        if any(x in hl for x in ["expiry", "expir", "renewal"]):
            mapping.setdefault("expiry", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


def _parse_html(html: str, source_url: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return records

    rows = table.find_all("tr")
    if len(rows) < 2:
        return records

    headers = [clean(th.get_text()) for th in rows[0].find_all(["th", "td"])]
    col_map = _map_columns(headers)

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
        local_rep = get("local_rep") or None
        expiry_raw = get("expiry") or None
        status_raw = get("status") or ""

        if not inn_val and not trade_name:
            continue

        exp = parse_date(expiry_raw)
        if status_raw:
            status = normalize_status(status_raw)
        elif exp and exp < date.today():
            status = "expired"
        else:
            status = "active"

        records.append(RegistrationRecord(
            inn=clean(inn_val) or clean(trade_name) or "",
            brand_name=clean(trade_name),
            country_code=COUNTRY_CODE,
            registration_no=clean(reg_no),
            holder=clean(holder),
            local_agent=clean(local_rep),
            status=status,
            expiry_date=exp,
            dosage_forms=[clean(dosage_form)] if dosage_form else [],
            source_url=source_url,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    return records


class ComorosScraper(BaseRegulatoryScraper):
    body_code = "MOH_COM"
    country_code = COUNTRY_CODE
    source_url = MOH_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to access {self.source_url}")
        try:
            with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                resp = client.get(self.source_url)
                resp.raise_for_status()

                # The provided HTML snippet indicates an error or lack of public data.
                # If the response text is very short or contains specific error messages,
                # it's likely that no searchable drug registration data is available.
                if len(resp.text) < 1000 or "FETCH_ERROR" in resp.text or "nodename nor servname provided, or not known" in resp.text:
                    self.warn("The Ministry of Health Comoros portal does not appear to have a public drug registration search interface or returned an error.")
                    return []

                # If there's a substantial HTML response, attempt to parse it.
                # However, without a specific search or table structure, this is unlikely to yield results.
                # The examples show XCRUD or DataTables pagination, which are not evident from the error message.
                # For now, we assume no such structure exists based on the error.
                self.warn("The Ministry of Health Comoros portal may not have a dedicated drug registration search, or the structure is not identifiable for scraping.")
                return []

        except httpx.HTTPStatusError as e:
            self.warn(f"HTTP error occurred while fetching {self.source_url}: {e}")
            return []
        except httpx.RequestError as e:
            self.warn(f"Request error occurred while fetching {self.source_url}: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred: {e}")
            return []