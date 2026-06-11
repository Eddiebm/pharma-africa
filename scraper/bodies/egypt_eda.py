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
APPLICANT_FIELD    = "ctl00$ContentPlaceHolder1$ui_txtApplicant"
CAPTCHA_FIELD      = "ctl00$ContentPlaceHolder1$txtimgcode"
SEARCH_BTN_FIELD   = "ctl00$ContentPlaceHolder1$ui_btnSearch"
GRIDVIEW_ID        = "ctl00$ContentPlaceHolder1$GridView1"

# Strategy: applicant (company) searches + INN generic name prefixes.
# Arabic prefix searches don't work — EDA stores names in English/Latin.
# Random letter combos (aaa, baa...) have <1 unique result per search on average.
# ~130 targeted searches vs 676 random ones — much higher yield per search.

# Top Egyptian pharma companies + MNC subsidiaries registered with EDA
APPLICANT_TERMS = [
    # Local Egyptian manufacturers
    "EIPICO", "CID", "Minapharm", "Pharco", "Memphis",
    "Kahira", "Delta", "Nile", "Arab", "Egyptian",
    "ATOS", "Amira", "Sigma", "Eva", "Global",
    "Medical", "Mina", "October", "Alexandria", "Cairo",
    "Rameda", "Adwia", "SEDICO", "MARCYRL", "Pfizer Egypt",
    # More local Egyptian manufacturers
    "Pharaonia", "Pharo", "Andalous", "Chemipharm", "Amoun",
    "Mash", "Averroes", "ATCO", "Zeta", "Utopia",
    "Biomed", "Apex", "Borg", "Medizen", "INAD",
    "Unipharma", "Gypto", "Amriya", "Misr", "Egyphar",
    "Organo", "NAPI", "Future", "Sunny", "Pharmacon",
    "Acdima", "Pellets", "MDI", "Amriya", "Vetopharm",
    # MNC subsidiaries
    "Pfizer", "Novartis", "Roche", "GlaxoSmithKline", "GSK",
    "AstraZeneca", "Sanofi", "MSD", "Abbott", "Bayer",
    "Johnson", "Boehringer", "Servier", "Amgen", "Lilly",
    "Merck", "Novo Nordisk", "Teva", "Hikma", "Sandoz",
    "Cipla", "Sun Pharma", "KRKA", "Richter", "Stada",
    "Fresenius", "Baxter", "Becton", "Medtronic", "Ipsen",
]

# Common INN/generic name 3-4 char prefixes with high drug coverage
INN_PREFIXES = [
    # Antibiotics / anti-infectives
    "amo", "amp", "pen", "cip", "cef", "azi", "cla", "van",
    "met", "tri", "sul", "nit", "flu", "tet", "str", "gen",
    "lev", "mox", "imi", "mer", "pip", "lin",
    # Cardiovascular
    "ate", "bis", "pro", "nar", "val", "ram", "lis", "cap",
    "eni", "tel", "can", "los", "irb", "nif", "amo",
    "ato", "sim", "ros", "pra", "fur", "hyd", "spi",
    # CNS
    "par", "ser", "ven", "esc", "flu", "cit", "dul",
    "ole", "ris", "que", "hal", "alp", "dia", "lor",
    "phe", "car", "val", "lam", "top", "gab",
    # Diabetes / metabolic
    "gli", "glip", "glib", "met", "sit", "emp", "dag",
    "ins", "lir", "exa", "pio",
    # GI / pain / other
    "ome", "lan", "pan", "eso", "rab", "dom", "ond",
    "ibu", "dic", "ket", "cel", "tra", "mor", "cod",
    "pre", "dex", "bet", "hyd", "mef", "ind",
    # HIV / antiviral
    "ten", "lam", "efa", "rit", "ata", "dol", "ral",
    # Antimalarials
    "art", "qui", "chl", "ato", "pri",
    # Vitamins / supplements
    "vit", "cal", "fer", "fol", "zin", "mag",
    # Additional broad coverage
    "acy", "alb", "ben", "col", "dap", "dox", "eth",
    "fex", "hep", "iso", "lit", "meb", "neb", "nys",
    "oxy", "ret", "tam", "thi", "var", "ace", "ald",
    "alk", "all", "ami", "ani", "ant", "apo", "arn",
    "asp", "ass", "bac", "bar", "bio", "bro", "bup",
    "but", "cab", "chl", "clo", "co-",
]
# Deduplicate while preserving order
_seen: set = set()
INN_PREFIXES = [x for x in INN_PREFIXES if not (x in _seen or _seen.add(x))]

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
    # ASP.NET GridView — actual rendered ID on EDA portal
    table = soup.find("table", {"id": "ContentPlaceHolder1_ui_GVDrugsData"})
    if table:
        return table

    # Fallback: find a table where each header cell is a short column label
    # (not the outer form table which has one massive cell containing all the HTML)
    for table in soup.find_all("table"):
        rows = table.find_all("tr", recursive=False)
        if len(rows) < 2:
            continue
        header_cells = rows[0].find_all(["th", "td"], recursive=False)
        if len(header_cells) < 3:
            continue
        # Skip if any header cell is a blob (form table characteristic)
        headers = [c.get_text().strip().lower() for c in header_cells]
        if any(len(h) > 40 for h in headers):
            continue
        if any(x in headers for x in ["trade name", "generic name", "reg no", "applicant"]):
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

    # (field_name, label, terms_list)
    search_plan = [
        (APPLICANT_FIELD, "applicant", APPLICANT_TERMS),
        (GENERIC_NAME_FIELD, "generic",  INN_PREFIXES),
        (TRADE_NAME_FIELD,  "trade",     INN_PREFIXES),
    ]

    for field_name, field_label, terms in search_plan:
        for term in terms:
            captcha = _solve_captcha(client, api_key)
            if not captcha:
                log.warning(f"CAPTCHA solve failed for '{term}', skipping")
                time.sleep(2)
                continue

            recs, _ = _search_term(
                client, field_name, term, captcha, current_html
            )
            new = 0
            for r in recs:
                key = r.registration_no or f"{r.inn}|{r.brand_name}"
                if key not in seen:
                    seen.add(key)
                    all_records.append(r)
                    new += 1

            log.info(f"[EDA_EG] {field_label} '{term}': {new} new (total {len(all_records)})")

            # Refresh base page to keep session alive
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
