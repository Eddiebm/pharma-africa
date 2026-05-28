"""
Senegal — ARP (Agence sénégalaise de Réglementation Pharmaceutique)
Source: https://arp.sn/liste-des-amms/
Type: WordPress page with DataTables HTML table (all ~7,459 rows pre-loaded)
Columns: NOM DU MEDICAMENT, Numero AMM, Prix Public, DCI2, dosage,
         présentation, Forme Galénique, Voie d'administration,
         Laboratoire, classe thérapeutique, RCP, PHOTO
"""
import logging
from datetime import date

import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import clean

COUNTRY_CODE = "SN"
SOURCE_URL   = "https://arp.sn/liste-des-amms/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def _parse_table(html: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        logging.warning("[ARP_SN] No table found on page")
        return records

    rows = table.find_all("tr")
    if len(rows) < 2:
        return records

    headers = [clean(th.get_text()) for th in rows[0].find_all(["th", "td"])]
    col: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["nom du med", "nom medicament", "medicament"]) and "col" not in col:
            col.setdefault("brand", i)
        if any(x in hl for x in ["numero amm", "n° amm", "amm"]):
            col.setdefault("reg_no", i)
        if any(x in hl for x in ["dci", "dénomination commune", "principe actif"]):
            col.setdefault("inn", i)
        if any(x in hl for x in ["forme gal", "forme pharm"]):
            col.setdefault("form", i)
        if any(x in hl for x in ["laboratoire", "labo", "fabricant", "titulaire"]):
            col.setdefault("holder", i)
        if any(x in hl for x in ["dosage", "concentration"]):
            col.setdefault("dosage", i)
        if any(x in hl for x in ["présentation", "presentation", "conditionnement"]):
            col.setdefault("presentation", i)
        if any(x in hl for x in ["classe", "category", "thérapeutique"]):
            col.setdefault("category", i)

    for row in rows[1:]:
        cells = [clean(td.get_text()) for td in row.find_all("td")]
        if not cells or len(cells) < 2:
            continue

        def get(key: str) -> str:
            idx = col.get(key)
            return cells[idx] if idx is not None and idx < len(cells) else ""

        brand   = get("brand")
        inn_val = get("inn")
        reg_no  = get("reg_no") or None
        holder  = get("holder") or None
        form    = get("form")
        dosage  = get("dosage")
        pres    = get("presentation")

        if not inn_val and not brand:
            continue

        # Skip rows that are clearly not drug records
        if brand and len(brand) > 200:
            continue

        form_parts = [p for p in [form, dosage, pres] if p]
        dosage_forms = [" / ".join(form_parts[:2])] if form_parts else []

        records.append(RegistrationRecord(
            inn=inn_val or brand,
            brand_name=brand or None,
            country_code=COUNTRY_CODE,
            registration_no=reg_no,
            holder=holder,
            local_agent=None,
            status="active",
            expiry_date=None,
            dosage_forms=dosage_forms,
            source_url=SOURCE_URL,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    return records


class SenegalARPScraper(BaseRegulatoryScraper):
    body_code = "ARP_SN"
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Fetching {SOURCE_URL}")
        with httpx.Client(
            verify=False,
            follow_redirects=True,
            timeout=60,
            headers=HEADERS,
        ) as client:
            resp = client.get(SOURCE_URL)
            resp.raise_for_status()

        records = _parse_table(resp.text)
        self.log(f"Total fetched: {len(records)}")
        return records
