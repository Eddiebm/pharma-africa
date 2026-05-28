"""
Tanzania Medicines and Medical Devices Authority (TMDA)
Source 1: PDF list of newly registered products
  https://www.tmda.go.tz/uploads/publications/en1587034176-list%20of%20newly%20registered%20products.pdf
Source 2: EAC harmonised products registered under TMDA
  https://www.tmda.go.tz/uploads/files/LIST%20OF%20MEDICINAL%20PRODUCTS%20REGISTERED%20UNDER%20EAC.pdf
Source 3: Live product_links page (try first, often times out)
  https://www.tmda.go.tz/product_links
"""
import io
import re
import logging
from datetime import date
import httpx
import pdfplumber
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "TZ"
PDF_URLS = [
    (
        "https://www.tmda.go.tz/uploads/publications/en1587034176-list%20of%20newly%20registered%20products.pdf",
        "Newly Registered Products",
    ),
    (
        "https://www.tmda.go.tz/uploads/files/LIST%20OF%20MEDICINAL%20PRODUCTS%20REGISTERED%20UNDER%20EAC.pdf",
        "EAC Harmonised Products",
    ),
]
PRODUCT_LINKS_URL = "https://www.tmda.go.tz/product_links"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
}


def _fetch_product_links_page(client: httpx.Client) -> list[str]:
    """Try to get direct PDF links from the product_links page."""
    try:
        resp = client.get(PRODUCT_LINKS_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                full = href if href.startswith("http") else "https://www.tmda.go.tz" + href
                pdf_links.append(full)
        return pdf_links
    except Exception as e:
        logging.warning(f"[TMDA_TZ] product_links page failed: {e}")
        return []


def _download_pdfs(client: httpx.Client) -> list[tuple[bytes, str]]:
    results = []

    # Try to find additional PDFs from the product links page
    extra_urls = _fetch_product_links_page(client)
    all_pdf_sources = [(u, f"product_links: {u}") for u in extra_urls] + PDF_URLS

    for url, label in all_pdf_sources:
        try:
            resp = client.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
                logging.info(f"[TMDA_TZ] Downloaded PDF: {label} ({len(resp.content)//1024}KB)")
                results.append((resp.content, url))
        except Exception as e:
            logging.warning(f"[TMDA_TZ] PDF download failed {url}: {e}")

    return results


def _parse_pdf(pdf_bytes: bytes, source_url: str) -> list[RegistrationRecord]:
    records: list[RegistrationRecord] = []
    seen_reg_nos: set[str] = set()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        headers: list[str] = []

        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                for row in table:
                    if not row:
                        continue
                    cells = [clean(str(c or "")) for c in row]

                    # Detect or refresh headers
                    if not headers or _is_header_row(cells):
                        row_text = " ".join(cells).lower()
                        if any(x in row_text for x in ["product", "trade", "inn", "registration", "reg no", "substance"]):
                            headers = cells
                            continue

                    if not headers:
                        continue

                    col_map = _map_columns(headers)

                    def get(key: str) -> str:
                        idx = col_map.get(key)
                        if idx is None or idx >= len(cells):
                            return ""
                        return cells[idx]

                    reg_no = get("reg_no") or None
                    trade_name = get("trade_name") or None
                    inn_val = get("inn") or ""
                    dosage_form = get("dosage_form") or ""
                    holder = get("holder") or None
                    expiry_raw = get("expiry") or None
                    status_raw = get("status") or ""

                    if not inn_val and not trade_name:
                        continue
                    if inn_val.lower() in ("inn", "generic name", "active ingredient"):
                        continue

                    # Deduplicate by reg_no
                    dedup_key = reg_no or f"{inn_val}|{trade_name}"
                    if dedup_key in seen_reg_nos:
                        continue
                    seen_reg_nos.add(dedup_key)

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
                        source_type="document",
                        raw=dict(zip(headers[:len(cells)], cells)),
                    ))

    return records


def _is_header_row(cells: list[str]) -> bool:
    row_text = " ".join(cells).lower()
    header_keywords = ["product name", "trade name", "inn", "reg no", "registration no", "substance"]
    return sum(1 for k in header_keywords if k in row_text) >= 2


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["reg no", "registration no", "reg. no", "tmda no", "product no"]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["trade name", "product name", "brand", "commercial"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["inn", "generic", "active ingr", "substance", "api"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form", "presentation"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["holder", "manufacturer", "company", "applicant", "marketer"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["expiry", "renewal", "valid", "expir"]):
            mapping.setdefault("expiry", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


class TanzaniaTMDAScraper(BaseRegulatoryScraper):
    body_code = "TMDA_TZ"
    country_code = COUNTRY_CODE
    source_url = PRODUCT_LINKS_URL

    def fetch(self) -> list[RegistrationRecord]:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            self.log("Downloading Tanzania TMDA PDFs...")
            pdfs = _download_pdfs(client)

        if not pdfs:
            raise RuntimeError("No TMDA PDFs could be downloaded")

        all_records: list[RegistrationRecord] = []
        seen_reg_nos: set[str] = set()
        for pdf_bytes, url in pdfs:
            self.log(f"Parsing {url} ({len(pdf_bytes)//1024}KB)")
            page_records = _parse_pdf(pdf_bytes, url)
            # global dedup across PDFs
            for r in page_records:
                key = r.registration_no or f"{r.inn}|{r.brand_name}"
                if key not in seen_reg_nos:
                    seen_reg_nos.add(key)
                    all_records.append(r)
            self.log(f"Running total: {len(all_records)}")

        self.log(f"Total fetched: {len(all_records)}")
        return all_records
