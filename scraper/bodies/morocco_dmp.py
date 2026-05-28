"""
Morocco DMP (Direction du Médicament et de la Pharmacie) — Medicine Register
Primary source: Open-data XLSX from data.gov.ma (ODbL licensed, CNOPS reimbursement list)
  https://data.gov.ma/data/fr/dataset/referentiel-des-medicaments
Secondary: DMP search portal dmp.sante.gov.ma (if reachable)
"""
import io
import logging
import httpx
import openpyxl

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "MA"
XLSX_URL = (
    "https://data.gov.ma/data/fr/dataset/2cdfd9f4-289d-4e9a-8998-50bd03f8e874"
    "/resource/094733f5-5434-4163-b837-df0e7b665127/download/ref-des-medicaments-cnops-2014.xlsx"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
}


def _parse_xlsx(xlsx_bytes: bytes) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return records

    # Find header row — first row with meaningful text
    header_row_idx = 0
    headers: list[str] = []
    for i, row in enumerate(rows):
        cells = [clean(str(c or "")) for c in row]
        row_text = " ".join(cells).lower()
        if any(x in row_text for x in ["code", "denomination", "dci", "forme", "titulaire", "lab"]):
            headers = cells
            header_row_idx = i
            break

    if not headers:
        # Fallback: use first row
        headers = [clean(str(c or "")) for c in rows[0]]
        header_row_idx = 0

    col_map = _map_columns(headers)
    logging.info(f"[DMP_MA] Headers: {headers}")
    logging.info(f"[DMP_MA] Col map: {col_map}")

    for row in rows[header_row_idx + 1:]:
        cells = [clean(str(c or "")) for c in row]
        if not any(cells):
            continue

        def get(key: str) -> str:
            idx = col_map.get(key)
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx]

        reg_no = get("reg_no") or None
        brand_name = get("brand_name") or None
        dci = get("dci") or ""  # DCI = INN in French
        dosage_form = get("dosage_form") or ""
        dosage_strength = get("strength") or ""
        holder = get("holder") or None
        status_raw = get("status") or ""

        if not dci and not brand_name:
            continue

        # Combine form + strength
        forms = []
        if dosage_form:
            forms.append(clean(dosage_form))

        status = normalize_status(status_raw) if status_raw else "active"

        records.append(RegistrationRecord(
            inn=clean(dci) or clean(brand_name) or "",
            brand_name=clean(brand_name),
            country_code=COUNTRY_CODE,
            registration_no=clean(reg_no),
            holder=clean(holder),
            local_agent=None,
            status=status,
            expiry_date=None,
            dosage_forms=forms,
            source_url=XLSX_URL,
            source_type="document",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    wb.close()
    return records


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["code amm", "num amm", "amm", "autorisation", "ref", "code"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["denomination", "nom com", "marque", "brand", "specialite", "spécialité", "libelle", "nom"]):
            mapping.setdefault("brand_name", i)
        if any(x in hl for x in ["dci", "inn", "substance", "principe actif", "generique", "generique"]):
            mapping.setdefault("dci", i)
        if any(x in hl for x in ["forme", "form"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["dosage", "teneur", "concentration", "strength"]):
            mapping.setdefault("strength", i)
        if any(x in hl for x in ["titulaire", "laboratoire", "fabricant", "holder", "lab"]):
            mapping.setdefault("holder", i)
        if "status" in hl or "statut" in hl or "etat" in hl or "état" in hl:
            mapping.setdefault("status", i)
    return mapping


class MoroccoDMPScraper(BaseRegulatoryScraper):
    body_code = "DMP_MA"
    country_code = COUNTRY_CODE
    source_url = XLSX_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log("Downloading Morocco DMP XLSX from open-data portal...")
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(XLSX_URL, headers=HEADERS)
            if resp.status_code != 200:
                raise RuntimeError(f"XLSX download failed: HTTP {resp.status_code}")
            content_type = resp.headers.get("content-type", "")
            if "html" in content_type:
                raise RuntimeError(f"Got HTML instead of XLSX (content-type: {content_type})")

        self.log(f"Downloaded {len(resp.content)//1024}KB")
        records = _parse_xlsx(resp.content)
        self.log(f"Parsed {len(records)} records")
        return records
