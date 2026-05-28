"""
Ghana Food and Drugs Authority (FDA Ghana)
Product register portal (SSL expired, bypass with verify=False):
  https://verifypermit.fdaghana.gov.gh/publicsearch
  http://196.61.32.245:55/publicsearch  (raw IP fallback)
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "GH"
PORTAL_URLS = [
    "https://verifypermit.fdaghana.gov.gh/publicsearch",
    "http://verifypermit.fdaghana.gov.gh/publicsearch",
    "http://196.61.32.245:55/publicsearch",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


def _find_working_portal(client: httpx.Client) -> str | None:
    for url in PORTAL_URLS:
        try:
            resp = client.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200 and len(resp.text) > 500:
                logging.info(f"[FDA_GH] Working portal: {url}")
                return url
        except Exception as e:
            logging.warning(f"[FDA_GH] {url} failed: {e}")
    return None


def _scrape_portal(client: httpx.Client, base_url: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    soup = BeautifulSoup(client.get(base_url, headers=HEADERS, timeout=30).text, "lxml")

    # Detect pagination type
    # 1. DataTables JSON
    records = _try_datatables(client, base_url)
    if records:
        return records

    # 2. XCRUD AJAX
    xcrud_key = None
    for inp in soup.find_all("input", class_="xcrud-data"):
        if inp.get("name") == "key":
            xcrud_key = inp.get("value", "")
    if xcrud_key:
        records = _try_xcrud(client, base_url, xcrud_key)
        if records:
            return records

    # 3. Static HTML table
    records = _parse_table(soup.decode() if hasattr(soup, "decode") else str(soup), base_url)
    return records


def _try_datatables(client: httpx.Client, base_url: str) -> list[RegistrationRecord]:
    """Laravel DataTables GET — columns: client_name, product_name, product_category, expiry_date, status"""
    records: list[RegistrationRecord] = []
    start = 0
    length = 100
    for page in range(500):
        try:
            params = {
                "draw": str(page + 1),
                "start": str(start),
                "length": str(length),
                "search[value]": "",
                "search[regex]": "false",
                "columns[0][data]": "DT_RowIndex",
                "columns[1][data]": "client_name",
                "columns[2][data]": "product_name",
                "columns[3][data]": "product_category",
                "columns[4][data]": "expiry_date",
                "columns[5][data]": "status",
            }
            resp = client.get(
                base_url,
                params=params,
                headers={**HEADERS, "X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("data", [])
            if not rows:
                break
            for row in rows:
                r = _parse_json_row(row, base_url)
                if r:
                    records.append(r)
            start += length
            if start >= data.get("recordsTotal", 0):
                break
        except Exception as e:
            logging.warning(f"[FDA_GH] DataTables start={start} failed: {e}")
            break
    return records


def _try_xcrud(client: httpx.Client, base_url: str, key: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    # Derive XCRUD AJAX URL
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    xcrud_ajax = f"{parsed.scheme}://{parsed.netloc}/xcrud/xcrud_ajax.php"

    start = 0
    limit = 100
    for _ in range(200):
        data = {"key": key, "start": str(start), "limit": str(limit)}
        try:
            resp = client.post(xcrud_ajax, data=data, headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"}, timeout=30)
            resp.raise_for_status()
            page_recs = _parse_table(resp.text, base_url)
            if not page_recs:
                break
            records.extend(page_recs)
            start += limit
        except Exception as e:
            logging.warning(f"[FDA_GH] XCRUD start={start} failed: {e}")
            break
    return records


def _parse_table(html: str, source_url: str) -> list[RegistrationRecord]:
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
            local_agent=None,
            status=status,
            expiry_date=exp,
            dosage_forms=[clean(dosage_form)] if dosage_form else [],
            source_url=source_url,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    return records


def _parse_json_row(row, source_url: str) -> RegistrationRecord | None:
    if isinstance(row, list):
        if len(row) < 3:
            return None
        trade_name  = clean(str(row[0]))
        inn_val     = clean(str(row[1])) if len(row) > 1 else ""
        reg_no      = clean(str(row[2])) if len(row) > 2 else None
        dosage_form = clean(str(row[3])) if len(row) > 3 else ""
        holder      = clean(str(row[4])) if len(row) > 4 else ""
        expiry_raw  = str(row[5]) if len(row) > 5 else ""
        status_raw  = str(row[6]) if len(row) > 6 else ""
    elif isinstance(row, dict):
        trade_name  = clean(str(row.get("product_name", row.get("brand_name", row.get("trade_name", "")))))
        inn_val     = clean(str(row.get("active_ingredient", row.get("inn", row.get("generic_name", "")))))
        reg_no      = clean(str(row.get("registration_no", row.get("cert_no", row.get("reg_no", ""))))) or None
        dosage_form = clean(str(row.get("dosage_form", row.get("form", ""))))
        holder      = clean(str(row.get("company", row.get("holder", row.get("applicant", "")))))
        expiry_raw  = str(row.get("expiry_date", row.get("expiry", "")))
        status_raw  = str(row.get("status", ""))
    else:
        return None

    if not inn_val and not trade_name:
        return None

    exp = parse_date(expiry_raw)
    status = normalize_status(status_raw) if status_raw else (
        "expired" if (exp and exp < date.today()) else "active"
    )

    return RegistrationRecord(
        inn=inn_val or trade_name,
        brand_name=trade_name or None,
        country_code=COUNTRY_CODE,
        registration_no=reg_no,
        holder=holder or None,
        local_agent=None,
        status=status,
        expiry_date=exp,
        dosage_forms=[dosage_form] if dosage_form else [],
        source_url=source_url,
        source_type="scrape",
        raw=row if isinstance(row, dict) else {},
    )


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration", "cert no", "permit", "licence", "license"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["brand", "trade name", "product name", "commercial"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["inn", "generic", "active ingr", "substance", "api"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form", "presentation"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["company", "holder", "applicant", "manufacturer"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["expiry", "expir", "renewal", "valid"]):
            mapping.setdefault("expiry", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


class GhanaFDAScraper(BaseRegulatoryScraper):
    body_code = "FDA_GH"
    country_code = COUNTRY_CODE
    source_url = PORTAL_URLS[0]

    def fetch(self) -> list[RegistrationRecord]:
        with httpx.Client(timeout=20, follow_redirects=True, verify=False) as client:
            self.log("Finding working Ghana FDA portal...")
            working_url = _find_working_portal(client)
            if not working_url:
                raise RuntimeError("All Ghana FDA portal URLs failed — SSL expired and raw IP unreachable")
            records = _scrape_portal(client, working_url)

        self.log(f"Total fetched: {len(records)}")
        return records
