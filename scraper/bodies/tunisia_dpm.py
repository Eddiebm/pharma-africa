"""
Tunisia — DPM (Direction de la Pharmacie et du Médicament)
Source: https://dpm.tn/images/pdf/liste_amm.xls  (direct XLS download)
Type: Old-format Excel (.xls) — ~6,059 records
Columns: Nom, Dosage, Forme, Présentation, DCI, Classe, Sous Classe,
         Laboratoire, AMM, Date AMM, ...
"""
import io
import logging
from datetime import date

import httpx
import xlrd

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import clean

COUNTRY_CODE = "TN"
XLS_URL = "https://dpm.tn/images/pdf/liste_amm.xls"
SOURCE_URL = "https://dpm.tn/medicament/humain/liste-des-medicaments"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "*/*",
    "Referer": SOURCE_URL,
}


def _xl_date(wb, val) -> date | None:
    """Convert Excel serial date to Python date."""
    if not val:
        return None
    try:
        tup = xlrd.xldate_as_tuple(float(val), wb.datemode)
        if tup[0] == 0:
            return None
        return date(*tup[:3])
    except Exception:
        return None


def _parse_sheet(wb: xlrd.Book) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    ws = wb.sheet_by_index(0)

    if ws.nrows < 2:
        return records

    # Build column map from header row
    headers = [str(ws.cell_value(0, c)).strip().lower() for c in range(ws.ncols)]

    def col(names: list[str]) -> int | None:
        for name in names:
            for i, h in enumerate(headers):
                if name in h:
                    return i
        return None

    c_brand   = col(["nom"])
    c_inn     = col(["dci"])
    c_form    = col(["forme"])
    c_holder  = col(["laboratoire"])
    c_reg     = col(["amm"])
    c_date    = col(["date amm", "date"])
    c_class_  = col(["classe"])
    c_dosage  = col(["dosage"])

    for row_idx in range(1, ws.nrows):
        def get(c: int | None) -> str:
            if c is None or c >= ws.ncols:
                return ""
            return clean(str(ws.cell_value(row_idx, c)))

        brand   = get(c_brand)
        inn_val = get(c_inn)
        form    = get(c_form)
        holder  = get(c_holder)
        reg_no  = get(c_reg) or None
        dosage  = get(c_dosage)

        if not inn_val and not brand:
            continue

        # Date AMM is an Excel serial
        exp = None
        if c_date is not None and c_date < ws.ncols:
            raw_date = ws.cell_value(row_idx, c_date)
            if raw_date:
                exp = _xl_date(wb, raw_date)

        status = "expired" if (exp and exp < date.today()) else "active"

        # Build dosage form string
        form_parts = [p for p in [form, dosage] if p]
        dosage_forms = [" / ".join(form_parts)] if form_parts else []

        raw_row = {headers[c]: str(ws.cell_value(row_idx, c)) for c in range(ws.ncols)}

        records.append(RegistrationRecord(
            inn=inn_val or brand,
            brand_name=brand or None,
            country_code=COUNTRY_CODE,
            registration_no=reg_no,
            holder=holder or None,
            local_agent=None,
            status=status,
            expiry_date=exp,
            dosage_forms=dosage_forms,
            source_url=SOURCE_URL,
            source_type="scrape",
            raw=raw_row,
        ))

    return records


class TunisiaDPMScraper(BaseRegulatoryScraper):
    body_code = "DPM_TN"
    country_code = COUNTRY_CODE
    source_url = SOURCE_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Downloading XLS from {XLS_URL}")
        with httpx.Client(verify=False, follow_redirects=True, timeout=60,
                          headers=HEADERS) as client:
            resp = client.get(XLS_URL)
            resp.raise_for_status()
            self.log(f"Downloaded {len(resp.content):,} bytes")

        wb = xlrd.open_workbook(file_contents=resp.content)
        records = _parse_sheet(wb)
        self.log(f"Total fetched: {len(records)}")
        return records
