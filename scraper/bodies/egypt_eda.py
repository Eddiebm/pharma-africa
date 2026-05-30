"""
Egypt — EDA (Egyptian Drug Authority)
Portal: http://eservices.edaegypt.gov.eg/EDASearch/SearchRegDrugs.aspx
Strategy: ASP.NET WebForms with image CAPTCHA (CImage.aspx).
  - Solve CAPTCHA via 2captcha.com image recognition API
  - Search by 3-letter prefix (a-z × 'aa') for trade name + generic name
  - Paginate via GridView __doPostBack (no new CAPTCHA needed for pages)
  - Requires env var: TWOCAPTCHA_KEY

Set TWOCAPTCHA_KEY in .env (or Hetzner env) to activate.
Without it the scraper logs a warning and returns 0 records.
"""
import base64
import logging
import re
import string
import time
from datetime import date

import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

import os

COUNTRY_CODE = "EG"
SEARCH_URL = "http://eservices.edaegypt.gov.eg/EDASearch/SearchRegDrugs.aspx"
CAPTCHA_URL = "http://eservices.edaegypt.gov.eg/EDASearch/CImage.aspx"
TWOCAPTCHA_URL = "http://2captcha.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TRADE_NAME_FIELD   = "ctl00$ContentPlaceHolder1$ui_txtTradeName"
GENERIC_NAME_FIELD = "ctl00$ContentPlaceHolder1$ui_txtGeneric"
CAPTCHA_FIELD      = "ctl00$ContentPlaceHolder1$txtimgcode"
SEARCH_BTN_FIELD   = "ctl00$ContentPlaceHolder1$ui_btnSearch"
GRIDVIEW_ID        = "ctl00$ContentPlaceHolder1$GridView1"

# Arabic prefixes cover Egyptian drug names; English covers foreign/branded drugs.
# 55 total searches vs 676 before — runs in ~30min instead of 2.5 hours.
ARABIC_LETTERS = ["ا", "أ", "ب", "ت", "ث", "ج", "ح", "خ",
                  "د", "ذ", "ر", "ز", "س", "ش", "ص", "ض",
                  "ط", "ظ", "ع", "غ", "ف", "ق", "ك", "ل",
                  "م", "ن", "ه", "و", "ي"]
ARABIC_PREFIXES = [l + "ا" for l in ARABIC_LETTERS]
ENGLISH_PREFIXES = [chr(c) + "aa" for c in range(ord("a"), ord("z") + 1)]
SEARCH_PREFIXES = ARABIC_PREFIXES + ENGLISH_PREFIXES

log = logging.getLogger("EDA_EG")


def _solve_captcha(client: httpx.Client, api_key: str) -> str | None:
    """Download CImage.aspx and solve via 2captcha. Returns solution string or None."""
    try:
        img_resp = client.get(CAPTCHA_URL, timeout=15)
        img_resp.raise_for_status()
        img_b64 = base64.b64encode(img_resp.content).decode()
    except Exception as e:
        log.warning(f"CAPTCHA image download failed: {e}")
        return None

    # Submit to 2captcha
    try:
        submit = httpx.post(
            f"{TWOCAPTCHA_URL}/in.php",
            data={"key": api_key, "method": "base64", "body": img_b64},
            timeout=20,
        )
        submit.raise_for_status()
        if not submit.text.startswith("OK|"):
            log.warning(f"2captcha submit error: {submit.text}")
            return None
        captcha_id = submit.text.split("|")[1]
    except Exception as e:
        log.warning(f"2captcha submit failed: {e}")
        return None

    # Poll for result (up to 30 seconds)
    for _ in range(10):
        time.sleep(3)
        try:
            poll = httpx.get(
                f"{TWOCAPTCHA_URL}/res.php",
                params={"key": api_key, "action": "get", "id": captcha_id},
                timeout=10,
            )
            text = poll.text
            if text == "CAPCHA_NOT_READY":
                continue
            if text.startswith("OK|"):
                return text.split("|")[1]
            log.warning(f"2captcha poll error: {text}")
            return None
        except Exception as e:
            log.warning(f"2captcha poll failed: {e}")
            return None

    log.warning("2captcha timed out after 30s")
    return None


def _extract_hidden(soup: BeautifulSoup) -> dict:
    fields = {}
    for name in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION",
                 "__EVENTTARGET", "__EVENTARGUMENT"]:
        tag = soup.find("input", {"name": name})
        fields[name] = tag.get("value", "") if tag else ""
    return fields


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        if not h:
            continue
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration", "licence", "license", "decision"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["trade name", "product name", "brand", "commercial"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["generic name", "generic", "inn", "active ingredient"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "dosage", "form", "presentation"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["holder", "company", "applicant", "manufacturer"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["expiry", "expiration", "valid", "renewal"]):
            mapping.setdefault("expiry", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


def _find_results_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers_text = " ".join(
            c.get_text().strip().lower() for c in rows[0].find_all(["th", "td"])
        )
        if any(x in headers_text for x in ["trade name", "generic name", "reg no", "applicant"]):
            return table
    return None


def _parse_page(html: str) -> list[RegistrationRecord]:
    soup = BeautifulSoup(html, "lxml")
    table = _find_results_table(soup)
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    headers = [clean(c.get_text()) for c in rows[0].find_all(["th", "td"])]
    col = _map_columns(headers)
    records = []

    for row in rows[1:]:
        cells = [clean(td.get_text()) for td in row.find_all("td")]
        if not cells or len(cells) < 2:
            continue

        def get(key: str) -> str:
            idx = col.get(key)
            return cells[idx] if idx is not None and idx < len(cells) else ""

        reg_no     = get("reg_no") or None
        trade_name = get("trade_name") or None
        inn_val    = get("inn")
        dosage     = get("dosage_form")
        holder     = get("holder") or None
        status_raw = get("status")
        expiry_raw = get("expiry")

        if not inn_val and not trade_name:
            continue

        exp = parse_date(expiry_raw) if expiry_raw else None
        if status_raw:
            status = normalize_status(status_raw)
        elif exp and exp < date.today():
            status = "expired"
        else:
            status = "active"

        records.append(RegistrationRecord(
            inn=inn_val or trade_name or "",
            brand_name=trade_name,
            country_code=COUNTRY_CODE,
            registration_no=reg_no,
            holder=holder,
            local_agent=None,
            status=status,
            expiry_date=exp,
            dosage_forms=[dosage] if dosage else [],
            source_url=SEARCH_URL,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))
    return records


def _max_page(html: str) -> int:
    soup = BeautifulSoup(html, "lxml")
    links = soup.find_all("a", href=re.compile(r"Page\$\d+", re.I))
    if not links:
        pager = soup.find("tr", class_=re.compile(r"pager|pagination", re.I))
        if pager:
            nums = re.findall(r"\b(\d+)\b", pager.get_text())
            if nums:
                return max(int(n) for n in nums)
        return 1
    nums = []
    for a in links:
        for attr in ["href", "onclick"]:
            m = re.search(r"Page\$(\d+)", a.get(attr, ""), re.I)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) if nums else 1


def _search_term(
    client: httpx.Client, search_field: str, term: str,
    captcha_solution: str, initial_html: str
) -> tuple[list[RegistrationRecord], str]:
    """
    POST a search and paginate. Returns (records, last_html).
    Pagination via GridView __doPostBack does NOT need a new CAPTCHA.
    """
    records = []
    seen_keys: set[str] = set()
    soup0 = BeautifulSoup(initial_html, "lxml")
    hidden = _extract_hidden(soup0)
    post_headers = {**HEADERS, "Content-Type": "application/x-www-form-urlencoded"}

    # First page — submit search + CAPTCHA
    try:
        resp = client.post(
            SEARCH_URL,
            data={
                **hidden,
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                search_field: term,
                CAPTCHA_FIELD: captcha_solution,
                SEARCH_BTN_FIELD: "Search",
            },
            headers=post_headers,
            timeout=45,
        )
        resp.raise_for_status()
    except Exception as e:
        log.warning(f"Search '{term}' POST failed: {e}")
        return records, initial_html

    # Check if CAPTCHA was rejected
    if "incorrect" in resp.text.lower() or "invalid code" in resp.text.lower():
        log.warning(f"CAPTCHA rejected for term '{term}'")
        return records, initial_html

    page_recs = _parse_page(resp.text)
    last_html = resp.text

    for r in page_recs:
        key = r.registration_no or f"{r.inn}|{r.brand_name}"
        if key not in seen_keys:
            seen_keys.add(key)
            records.append(r)

    # Paginate (no new CAPTCHA needed — GridView postback reuses session)
    max_pg = _max_page(resp.text)
    for pg in range(2, min(max_pg + 1, 200)):
        hidden = _extract_hidden(BeautifulSoup(resp.text, "lxml"))
        try:
            resp = client.post(
                SEARCH_URL,
                data={
                    **hidden,
                    "__EVENTTARGET": GRIDVIEW_ID,
                    "__EVENTARGUMENT": f"Page${pg}",
                    search_field: term,
                },
                headers=post_headers,
                timeout=45,
            )
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"Page {pg} for '{term}' failed: {e}")
            break

        page_recs = _parse_page(resp.text)
        if not page_recs:
            break
        for r in page_recs:
            key = r.registration_no or f"{r.inn}|{r.brand_name}"
            if key not in seen_keys:
                seen_keys.add(key)
                records.append(r)

        last_html = resp.text
        if _max_page(resp.text) < pg:
            break

    return records, last_html


def _scrape_all(client: httpx.Client, api_key: str) -> list[RegistrationRecord]:
    all_records: list[RegistrationRecord] = []
    seen: set[str] = set()

    # Load initial page
    resp = client.get(SEARCH_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    current_html = resp.text

    for field_name, field_label in [
        (TRADE_NAME_FIELD, "trade"),
        (GENERIC_NAME_FIELD, "generic"),
    ]:
        for prefix in SEARCH_PREFIXES:
            # Each search needs a fresh CAPTCHA from the current session
            captcha = _solve_captcha(client, api_key)
            if not captcha:
                log.warning(f"CAPTCHA solve failed for prefix '{prefix}', skipping")
                time.sleep(2)
                continue

            recs, last_html = _search_term(
                client, field_name, prefix, captcha, current_html
            )
            new = 0
            for r in recs:
                key = r.registration_no or f"{r.inn}|{r.brand_name}"
                if key not in seen:
                    seen.add(key)
                    all_records.append(r)
                    new += 1

            log.info(f"[EDA_EG] {field_label} '{prefix}': {new} new (total {len(all_records)})")

            # Refresh base page periodically to keep session fresh
            try:
                resp = client.get(SEARCH_URL, headers=HEADERS, timeout=30)
                if "__VIEWSTATE" in resp.text:
                    current_html = resp.text
            except Exception:
                pass

            time.sleep(1.0)

    return all_records


class EgyptEDAScraper(BaseRegulatoryScraper):
    body_code    = "EDA_EG"
    country_code = COUNTRY_CODE
    source_url   = SEARCH_URL

    def fetch(self) -> list[RegistrationRecord]:
        api_key = os.environ.get("TWOCAPTCHA_KEY", "").strip()
        if not api_key:
            log.warning(
                "TWOCAPTCHA_KEY not set — EDA_EG scraper inactive. "
                "Set it in .env to enable Egypt Drug Authority scraping."
            )
            return []

        self.log("Connecting to Egypt EDA portal (with 2captcha)...")
        with httpx.Client(
            follow_redirects=True,
            verify=False,
            timeout=45,
        ) as client:
            records = _scrape_all(client, api_key)

        self.log(f"Total fetched: {len(records)}")
        return records
