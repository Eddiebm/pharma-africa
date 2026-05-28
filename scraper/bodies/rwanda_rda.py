"""
Rwanda Food and Drugs Authority (Rwanda FDA)
Active domain (confirmed May 2026): https://rwandafda.gov.rw
Register: https://rwandafda.gov.rw/register/monitoring_preview_register
~2,470 registered products (2,416 valid, 46 expiring, 8 in grace period)
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "RW"
REGISTER_URL = "https://rwandafda.gov.rw/register/monitoring_preview_register"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}

# XCRUD or DataTables pagination — will detect from page
AJAX_URL = "https://rwandafda.gov.rw/register/monitoring_preview_register"


def _scrape_all(client: httpx.Client) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []

    # Load first page
    resp = client.get(REGISTER_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "lxml")

    # Check for XCRUD
    xcrud_key = None
    for inp in soup.find_all("input", class_="xcrud-data"):
        if inp.get("name") == "key":
            xcrud_key = inp.get("value", "")
            break

    if xcrud_key:
        logging.info(f"[RDA_RW] Detected XCRUD pagination, key={xcrud_key[:16]}...")
        records = _scrape_xcrud(client, xcrud_key, html)
    else:
        # Try DataTables or plain HTML table
        records = _scrape_html_table(html)
        if not records:
            # Try DataTables AJAX
            records = _scrape_datatables(client, html)

    return records


def _scrape_xcrud(client: httpx.Client, key: str, first_html: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(first_html, "lxml")

    orderby = ""
    order = "desc"
    for inp in soup.find_all("input", class_="xcrud-data"):
        n = inp.get("name", "")
        if n == "orderby":
            orderby = inp.get("value", "")
        elif n == "order":
            order = inp.get("value", "")

    # Detect XCRUD AJAX endpoint (may differ per site)
    xcrud_ajax = "https://rwandafda.gov.rw/xcrud/xcrud_ajax.php"

    start = 0
    limit = 100
    for _ in range(200):  # max 20,000 records
        data = {"key": key, "orderby": orderby, "order": order, "start": str(start), "limit": str(limit)}
        try:
            resp = client.post(xcrud_ajax, data=data, headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"}, timeout=30)
            resp.raise_for_status()
            page_records = _parse_table(resp.text)
            if not page_records:
                break
            records.extend(page_records)
            start += limit
        except Exception as e:
            logging.warning(f"[RDA_RW] XCRUD page start={start} failed: {e}")
            break

    return records


def _scrape_datatables(client: httpx.Client, first_html: str) -> list[RegistrationRecord]:
    """Try DataTables server-side AJAX."""
    records: list[RegistrationRecord] = []
    start = 0
    length = 100

    for _ in range(100):
        try:
            resp = client.get(
                REGISTER_URL,
                params={"draw": "1", "start": str(start), "length": str(length), "search[value]": ""},
                headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("data", [])
            if not rows:
                break
            for row in rows:
                r = _parse_json_row(row)
                if r:
                    records.append(r)
            start += length
        except Exception as e:
            logging.warning(f"[RDA_RW] DataTables start={start} failed: {e}")
            break

    return records


def _scrape_html_table(html: str) -> list[RegistrationRecord]:
    """Parse a static HTML table (single page)."""
    soup = BeautifulSoup(html, "lxml")
    return _parse_table(html)


def _parse_table(html: str) -> list[RegistrationRecord]:
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

    if not col_map:
        return records

    for row in rows[1:]:
        cells = [clean(td.get_text()) for td in row.find_all("td")]
        if not cells or len(cells) < 2:
            continue

        def get(key: str) -> str:
            idx = col_map.get(key)
            return cells[idx] if idx is not None and idx < len(cells) else ""

        reg_no      = get("reg_no") or None
        trade_name  = get("trade_name") or None
        inn_val     = get("inn") or ""
        dosage_form = get("dosage_form") or ""
        holder      = get("holder") or None
        local_rep   = get("local_rep") or None
        expiry_raw  = get("expiry") or None
        status_raw  = get("status") or ""

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
            source_url=REGISTER_URL,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    return records


def _parse_json_row(row) -> RegistrationRecord | None:
    """Parse a DataTables JSON row (list or dict)."""
    if isinstance(row, list):
        # Positional: [brand, generic, strength, form, pack, manufacturer, country, reg_no, reg_date, expiry, agent]
        if len(row) < 8:
            return None
        trade_name  = clean(str(row[0]))
        inn_val     = clean(str(row[1]))
        dosage_form = clean(str(row[3])) if len(row) > 3 else ""
        holder      = clean(str(row[5])) if len(row) > 5 else ""
        reg_no      = clean(str(row[7])) if len(row) > 7 else None
        expiry_raw  = str(row[9]) if len(row) > 9 else ""
        local_rep   = clean(str(row[10])) if len(row) > 10 else ""
    elif isinstance(row, dict):
        trade_name  = clean(str(row.get("brand_name", row.get("trade_name", ""))))
        inn_val     = clean(str(row.get("generic_name", row.get("inn", ""))))
        dosage_form = clean(str(row.get("dosage_form", row.get("form", ""))))
        holder      = clean(str(row.get("manufacturer", row.get("holder", ""))))
        reg_no      = clean(str(row.get("registration_no", row.get("reg_no", "")))) or None
        expiry_raw  = str(row.get("expiry_date", row.get("expiry", "")))
        local_rep   = clean(str(row.get("local_agent", "")))
    else:
        return None

    if not inn_val and not trade_name:
        return None

    exp = parse_date(expiry_raw)
    status = "expired" if (exp and exp < date.today()) else "active"

    return RegistrationRecord(
        inn=inn_val or trade_name,
        brand_name=trade_name or None,
        country_code=COUNTRY_CODE,
        registration_no=reg_no,
        holder=holder or None,
        local_agent=local_rep or None,
        status=status,
        expiry_date=exp,
        dosage_forms=[dosage_form] if dosage_form else [],
        source_url=REGISTER_URL,
        source_type="scrape",
        raw=row if isinstance(row, dict) else {},
    )


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration no", "reg. no", "licence", "license"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["brand", "trade name", "product name", "commercial"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["inn", "generic", "active ingr", "substance", "api"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form", "presentation"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["mah", "manufacturer", "company", "holder", "applicant"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["local", "agent", "representative"]):
            mapping.setdefault("local_rep", i)
        if any(x in hl for x in ["expiry", "expir", "renewal", "valid"]):
            mapping.setdefault("expiry", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


class RwandaRDAScraper(BaseRegulatoryScraper):
    body_code = "RDA_RW"
    country_code = COUNTRY_CODE
    source_url = REGISTER_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Fetching Rwanda FDA register from {REGISTER_URL}")
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            records = _scrape_all(client)
        self.log(f"Total fetched: {len(records)}")
        return records
