"""
SAHPRA — South African Registered Veterinary Products
Source: sahpra.org.za/list-of-registered-veterinary-product/
Method: Ninja Tables AJAX — single GET returns all 357 records
Fields: applicationno, registrationnumber, productname, dosageform, company, ingredients
"""
import sys, os
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import normalize_status, clean

AJAX_URL = (
    "https://www.sahpra.org.za/wp-admin/admin-ajax.php"
    "?action=wp_ajax_ninja_tables_public_action"
    "&table_id=7111"
    "&target_action=get-all-data"
    "&default_sorting=old_first"
    "&skip_rows=0&limit_rows=0"
    "&ninja_table_public_nonce=0bbb86a021"
)
COUNTRY_CODE = "ZA"
SOURCE_URL = "https://www.sahpra.org.za/list-of-registered-veterinary-product/"


class SAHPRAVetScraper(BaseRegulatoryScraper):
    body_code = "SAHPRA_VET"
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> list[RegistrationRecord]:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(AJAX_URL, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            rows = resp.json()

        records = []
        for item in rows:
            v = item.get("value", {})
            reg_no = clean(v.get("registrationnumber"))
            brand = clean(v.get("productname"))
            if not reg_no and not brand:
                continue
            inn_raw = clean(v.get("ingredients", ""))
            records.append(RegistrationRecord(
                inn=inn_raw[:500] if inn_raw else "",
                brand_name=brand,
                country_code=COUNTRY_CODE,
                registration_no="VET-" + reg_no if reg_no else None,
                holder=clean(v.get("company")),
                local_agent=None,
                status="active",
                expiry_date=None,
                dosage_forms=[clean(v.get("dosageform"))] if v.get("dosageform") else [],
                source_url=SOURCE_URL,
                source_type="scrape",
                raw=v,
            ))

        self.log(f"SAHPRA vet: {len(records)} records")
        return records
