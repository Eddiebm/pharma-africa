"""
Kenya Pharmacy and Poisons Board (PPB) — Human Medicine Register
Source: products.pharmacyboardkenya.org/ppb_admin/pages/public_view_retention_products.php
Pagination: XCRUD AJAX framework — POST to xcrud_ajax.php with key + start offset
Total: ~2,560 human + ~2,560 herbal = ~5,120 records
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

BASE_URL  = "https://products.pharmacyboardkenya.org/ppb_admin/pages/public_view_retention_products.php"
HERBAL_URL = "https://products.pharmacyboardkenya.org/ppb_admin/pages/public_view_herbal.php"
AJAX_URL  = "https://products.pharmacyboardkenya.org/ppb_admin/xcrud/xcrud_ajax.php"
COUNTRY_CODE = "KE"
PAGE_SIZE = 100   # XCRUD supports up to 100 per request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml",
    "X-Requested-With": "XMLHttpRequest",
}


def _get_xcrud_params(client: httpx.Client, page_url: str) -> dict[str, str]:
    """Load the register page and extract ALL xcrud-data hidden field values."""
    resp = client.get(page_url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    params: dict[str, str] = {}
    for inp in soup.find_all("input", class_="xcrud-data"):
        name = inp.get("name", "")
        val  = inp.get("value", "")
        if name:
            params[name] = val
    return params


def _post_page(client: httpx.Client, params: dict[str, str], start: int, referer: str) -> str | None:
    """POST to XCRUD AJAX using xcrud[param] nested format. Returns HTML or None."""
    # XCRUD expects params nested as xcrud[key]=val
    data = {f"xcrud[{k}]": v for k, v in params.items()}
    data["xcrud[start]"] = str(start)
    data["xcrud[limit]"] = str(PAGE_SIZE)
    data["xcrud[task]"] = "list"
    try:
        resp = client.post(
            AJAX_URL,
            data=data,
            headers={**HEADERS, "Referer": referer, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        if "Wrong request" in resp.text:
            logging.warning(f"[PPB_KE] XCRUD wrong request at start={start}")
            return None
        return resp.text
    except Exception as e:
        logging.warning(f"[PPB_KE] AJAX POST start={start} failed: {e}")
        return None


def _update_params_from_response(html: str, params: dict[str, str]) -> dict[str, str]:
    """XCRUD rotates the key/instance on each response. Extract new values."""
    soup = BeautifulSoup(html, "lxml")
    new_params = dict(params)
    for inp in soup.find_all("input", class_="xcrud-data"):
        name = inp.get("name", "")
        val  = inp.get("value", "")
        if name and val:
            new_params[name] = val
    return new_params


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
            source_url=source_url,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    return records


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


def _scrape_register(client: httpx.Client, page_url: str, label: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    logging.info(f"[PPB_KE] Loading {label} page...")
    xcrud_params = _get_xcrud_params(client, page_url)

    if not xcrud_params.get("key"):
        logging.warning(f"[PPB_KE] No XCRUD key found on {page_url}")
        return records

    start = 0
    max_iterations = 200  # safety cap: 200 × 100 = 20,000 records

    for _ in range(max_iterations):
        html = _post_page(client, xcrud_params, start, page_url)
        if not html:
            break
        page_recs = _parse_html(html, page_url)
        if not page_recs:
            break
        records.extend(page_recs)
        # Update params with rotated key from response
        xcrud_params = _update_params_from_response(html, xcrud_params)
        start += PAGE_SIZE

    logging.info(f"[PPB_KE] {label}: {len(records)} records")
    return records


class KenyaPPBScraper(BaseRegulatoryScraper):
    body_code = "PPB_KE"
    country_code = COUNTRY_CODE
    source_url = BASE_URL

    def fetch(self) -> list[RegistrationRecord]:
        records: list[RegistrationRecord] = []
        with httpx.Client(timeout=30, follow_redirects=True, verify=False) as client:
            records.extend(_scrape_register(client, BASE_URL,   "Human Medicines"))
            records.extend(_scrape_register(client, HERBAL_URL, "Herbal Medicines"))

        self.log(f"Total fetched: {len(records)}")
        return records
