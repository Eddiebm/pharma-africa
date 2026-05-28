"""
NAFDAC — National Agency for Food and Drug Administration and Control (Nigeria)
Register: https://greenbook.nafdac.gov.ng
Endpoint: GET / with X-Requested-With: XMLHttpRequest + DataTables params
          Returns JSON with 9,058 registered products.
Fields:   product_name, NAFDAC (reg no), ingredient_name, applicant_name,
          form_name, status, approval_date, expiry_date, atc, composition
Strategy: Single paginated GET loop — no Playwright, no seeds needed.
Schedule: daily
"""
import os
import sys
from typing import Optional

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import clean, parse_date, normalize_status

GREENBOOK_URL = "https://greenbook.nafdac.gov.ng"
PAGE_SIZE = 500
AJAX_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


class NAFDACScraper(BaseRegulatoryScraper):
    body_code = "NAFDAC"
    country_code = "NG"
    source_url = GREENBOOK_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Starting NAFDAC fetch")
        records: list[RegistrationRecord] = []
        start = 0
        total = None

        while True:
            payload = self._get_page(start)
            if payload is None:
                break

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

    def _get_page(self, start: int) -> Optional[dict]:
        """Fresh connection per page — NAFDAC drops keep-alive between pages."""
        import time
        for attempt in range(3):
            try:
                if attempt:
                    time.sleep(2 ** attempt)
                with httpx.Client(timeout=30, follow_redirects=True) as client:
                    resp = client.get(
                        GREENBOOK_URL,
                        params={"draw": str(start // PAGE_SIZE + 1), "start": str(start), "length": str(PAGE_SIZE), "search[value]": ""},
                        headers=AJAX_HEADERS,
                    )
                    resp.raise_for_status()
                    return resp.json()
            except Exception as e:
                self.warn(f"Page start={start} attempt {attempt+1} failed: {e}")
        return None

    def _normalize(self, row: dict) -> Optional[RegistrationRecord]:
        brand  = clean(row.get("product_name", "").replace("##", "").strip())
        reg_no = clean(row.get("NAFDAC"))
        inn    = clean(row.get("ingredient_name") or (row.get("ingredient") or {}).get("ingredient_name"))
        holder = clean(row.get("applicant_name") or (row.get("applicant") or {}).get("name"))
        dosage = [row["form_name"]] if row.get("form_name") else []

        if not brand and not reg_no:
            return None

        return RegistrationRecord(
            inn=inn or "",
            brand_name=brand,
            country_code=self.country_code,
            registration_no=reg_no,
            holder=holder,
            local_agent=None,
            status=normalize_status(clean(row.get("status"))),
            expiry_date=parse_date(row.get("expiry_date")),
            dosage_forms=dosage,
            source_url=self.source_url,
            source_type="scrape",
            raw=row,
        )


    # ------------------------------------------------------------------
    # DEAD CODE — kept for reference, no longer called
    # ------------------------------------------------------------------
    def _fetch_via_wpdatatable(self) -> list[RegistrationRecord]:
        records = []
        start = 0
        length = 500

        with httpx.Client(timeout=30) as client:
            while True:
                resp = client.post(WPDATATABLE_AJAX, data={
                    "action": "get_wdtable",
                    "table_id": "1",
                    "draw": str(start // length + 1),
                    "start": str(start),
                    "length": str(length),
                })
                resp.raise_for_status()
                payload = resp.json()

                rows = payload.get("data", [])
                if not rows:
                    break

                for row in rows:
                    r = self._normalize_wpdatatable_row(row)
                    if r:
                        records.append(r)

                total = payload.get("recordsTotal", 0)
                start += length
                if start >= total:
                    break

        return records

    def _normalize_wpdatatable_row(self, row) -> Optional[RegistrationRecord]:
        # WPDataTables returns rows as lists or dicts depending on config
        if isinstance(row, list):
            # positional: [product_name, active_ingredient, nrn, dosage_form, ...]
            data = {
                "brand_name": row[0] if len(row) > 0 else None,
                "inn": row[1] if len(row) > 1 else None,
                "registration_no": row[2] if len(row) > 2 else None,
                "dosage_form": row[3] if len(row) > 3 else None,
                "holder": row[4] if len(row) > 4 else None,
                "status": row[5] if len(row) > 5 else None,
                "expiry_date": row[6] if len(row) > 6 else None,
            }
        else:
            data = {k.lower().replace(" ", "_"): v for k, v in row.items()}

        inn = clean(data.get("inn") or data.get("active_ingredient") or data.get("active_ingredients"))
        brand = clean(data.get("brand_name") or data.get("product_name"))
        if not inn and not brand:
            return None

        return RegistrationRecord(
            inn=inn or "",
            brand_name=brand,
            country_code=self.country_code,
            registration_no=clean(data.get("registration_no") or data.get("nrn")),
            holder=clean(data.get("holder") or data.get("applicant_name")),
            local_agent=None,
            status=normalize_status(clean(data.get("status"))),
            expiry_date=parse_date(data.get("expiry_date") or data.get("approval_date")),
            dosage_forms=parse_dosage_forms(clean(data.get("dosage_form"))),
            source_url=WPDATATABLE_AJAX,
            source_type="scrape",
            raw=data,
        )

    # ------------------------------------------------------------------
    # Path B: Playwright XHR intercept → direct API calls
    # ------------------------------------------------------------------
    async def _fetch_via_playwright(self) -> list[RegistrationRecord]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("playwright not installed — run: pip install playwright && playwright install chromium")

        self.log("Launching Playwright to discover Greenbook API endpoint")
        discovered_endpoint: Optional[str] = None
        discovered_params: dict = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Intercept all fetch/XHR responses to find the data API
            async def on_response(response):
                nonlocal discovered_endpoint, discovered_params
                if discovered_endpoint:
                    return
                url = response.url
                if "nafdac" not in url.lower():
                    return
                # Look for JSON responses that look like registration data
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                try:
                    body = await response.json()
                    # Check if it looks like drug records
                    sample = body if isinstance(body, list) else body.get("data", body.get("results", []))
                    if isinstance(sample, list) and len(sample) > 0:
                        first = sample[0] if sample else {}
                        if isinstance(first, dict) and any(
                            k.lower() in ("nrn", "productname", "activeingredient", "registrationno")
                            for k in first.keys()
                        ):
                            discovered_endpoint = url
                            self.log(f"Discovered API endpoint: {url}")
                except Exception:
                    pass

            page.on("response", on_response)
            await page.goto(GREENBOOK_URL, wait_until="networkidle", timeout=30000)
            await browser.close()

        if not discovered_endpoint:
            self.warn("Could not discover Greenbook API endpoint — site structure may have changed")
            return []

        # Now hit the discovered endpoint directly for each seed INN
        return await self._query_discovered_endpoint(discovered_endpoint)

    async def _query_discovered_endpoint(self, endpoint: str) -> list[RegistrationRecord]:
        inns = load_seed_inns()
        records = []
        self.log(f"Querying {len(inns)} INNs against {endpoint}")

        async with httpx.AsyncClient(timeout=20) as client:
            for inn in inns:
                try:
                    resp = await client.get(endpoint, params={"search": inn, "query": inn, "q": inn})
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("data", data.get("results", []))
                    for item in items:
                        r = self._normalize_greenbook_item(item, inn)
                        if r:
                            records.append(r)
                except Exception as e:
                    self.warn(f"Query failed for INN '{inn}': {e}")

        return records

    def _normalize_greenbook_item(self, item: dict, queried_inn: str) -> Optional[RegistrationRecord]:
        if not isinstance(item, dict):
            return None

        # Greenbook fields (as seen in the UI): ProductName, ActiveIngredients, NRN,
        # DosageForm, RouteOfAdministration, Strengths, ApplicantName, ApprovalDate, Status
        def get(*keys):
            for k in keys:
                for candidate in (k, k.lower(), k.replace(" ", ""), k.replace(" ", "_")):
                    v = clean(item.get(candidate))
                    if v:
                        return v
            return None

        inn = get("ActiveIngredients", "activeingredients", "active_ingredients") or queried_inn
        brand = get("ProductName", "productname", "product_name")
        if not inn and not brand:
            return None

        return RegistrationRecord(
            inn=inn,
            brand_name=brand,
            country_code=self.country_code,
            registration_no=get("NRN", "nrn", "RegistrationNo", "registrationno"),
            holder=get("ApplicantName", "applicantname", "applicant_name"),
            local_agent=None,
            status=normalize_status(get("Status", "status")),
            expiry_date=parse_date(get("ApprovalDate", "approvaldate", "ExpiryDate", "expirydate")),
            dosage_forms=parse_dosage_forms(get("DosageForm", "dosageform", "dosage_form")),
            source_url=self.source_url,
            source_type="scrape",
            raw=item,
        )


# Fallback if seeds/who_eml.csv is missing — core African-market drugs
FALLBACK_INNS = [
    "artemether", "lumefantrine", "artesunate", "quinine", "chloroquine",
    "amoxicillin", "ampicillin", "azithromycin", "ciprofloxacin", "metronidazole",
    "cotrimoxazole", "doxycycline", "tetracycline", "erythromycin", "clindamycin",
    "tenofovir", "lamivudine", "efavirenz", "nevirapine", "zidovudine",
    "abacavir", "lopinavir", "ritonavir", "dolutegravir", "atazanavir",
    "isoniazid", "rifampicin", "pyrazinamide", "ethambutol", "streptomycin",
    "paracetamol", "ibuprofen", "diclofenac", "morphine", "tramadol",
    "omeprazole", "metformin", "glibenclamide", "insulin", "amlodipine",
    "atorvastatin", "lisinopril", "hydrochlorothiazide", "salbutamol", "prednisolone",
    "dexamethasone", "diazepam", "phenobarbitone", "carbamazepine", "haloperidol",
    "oxytocin", "ergometrine", "misoprostol", "magnesium sulfate", "ferrous sulfate",
]
