"""
Namibia Medicines Regulatory Council (NRCS)
Portal URL: https://www.nmrc.com.na
The provided HTML snippet indicates a fetch error, suggesting the portal might be down or inaccessible via direct HTTP requests.
If the portal is only a static HTML page without a searchable database, the scraper will return an empty list.
If a search function exists, it will iterate through single letter prefixes to attempt to retrieve data.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "NAM"
BODY_CODE = "NRCS_NAM"
PORTAL_URL = "https://www.nmrc.com.na"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}

SEARCH_URL = "https://www.nmrc.com.na/registration_list.php" # Assuming this is the search page


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(x in hl for x in ["registration no", "reg. no.", "certificate no."]):
            mapping.setdefault("reg_no", i)
        if any(x in hl for x in ["brand name", "product name", "trade name"]):
            mapping.setdefault("trade_name", i)
        if any(x in hl for x in ["inn", "generic name", "active ingredient"]):
            mapping.setdefault("inn", i)
        if any(x in hl for x in ["dosage form", "form"]):
            mapping.setdefault("dosage_form", i)
        if any(x in hl for x in ["holder", "applicant", "company", "manufacturer"]):
            mapping.setdefault("holder", i)
        if any(x in hl for x in ["expiry date", "validity end", "valid until"]):
            mapping.setdefault("expiry", i)
        if "status" in hl:
            mapping.setdefault("status", i)
    return mapping


def _parse_html_table(html: str, source_url: str) -> list[RegistrationRecord]:
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
        logging.warning("[NRCS_NAM] Could not map columns from table headers.")
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
            status = "active" # Default to active if no specific status and not expired

        records.append(RegistrationRecord(
            inn=clean(inn_val) or clean(trade_name) or "",
            brand_name=clean(trade_name),
            country_code=COUNTRY_CODE,
            registration_no=clean(reg_no),
            holder=clean(holder),
            local_agent=None, # Not available
            status=status,
            expiry_date=exp,
            dosage_forms=[clean(dosage_form)] if dosage_form else [],
            source_url=source_url,
            source_type="scrape",
            raw=dict(zip(headers[:len(cells)], cells)),
        ))

    return records


class NamibiaScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        records: list[RegistrationRecord] = []
        seen_reg_nos: set[str] = set()

        try:
            with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                # Check if the main portal URL is accessible and not just an error page
                try:
                    resp = client.get(self.source_url, timeout=15)
                    resp.raise_for_status()
                    if "FETCH_ERROR" in resp.text or len(resp.text) < 500: # Basic check for a valid page
                        logging.warning(f"[NRCS_NAM] Portal homepage seems inaccessible or not a valid portal: {self.source_url}")
                        return []
                except httpx.HTTPStatusError as e:
                    logging.warning(f"[NRCS_NAM] Portal homepage returned error: {e}")
                    return []
                except httpx.RequestError as e:
                    logging.warning(f"[NRCS_NAM] Portal homepage request failed: {e}")
                    return []

                # Assuming the portal has a search page for products
                # We will iterate through single letters if direct search is not obvious
                # This assumes a POST request with a search term like 'search_term=a'
                logging.info(f"[NRCS_NAM] Attempting to search for products on {SEARCH_URL}")

                # Default to trying alphabetical search if no specific search form is found
                search_prefixes = list("abcdefghijklmnopqrstuvwxyz")

                for prefix in search_prefixes:
                    logging.info(f"[NRCS_NAM] Searching with prefix: '{prefix}'")
                    try:
                        # Assuming a form submission with a parameter like 'search_term'
                        # This part might need adjustment based on actual form structure
                        response = client.post(
                            SEARCH_URL,
                            data={"search_term": prefix},
                            headers={"Referer": self.source_url}, # Set referer if required
                            timeout=30
                        )
                        response.raise_for_status()
                        page_records = _parse_html_table(response.text, SEARCH_URL)

                        for record in page_records:
                            if record.registration_no and record.registration_no not in seen_reg_nos:
                                records.append(record)
                                seen_reg_nos.add(record.registration_no)
                            elif not record.registration_no:
                                # Log records without registration numbers if any, as they cannot be de-duplicated
                                logging.debug(f"[NRCS_NAM] Record without registration number: {record.inn or record.brand_name}")


                        if not page_records:
                            logging.info(f"[NRCS_NAM] No records found for prefix '{prefix}'")
                        else:
                            logging.info(f"[NRCS_NAM] Fetched {len(page_records)} records for prefix '{prefix}'")

                    except httpx.HTTPStatusError as e:
                        logging.warning(f"[NRCS_NAM] Search failed for prefix '{prefix}' (HTTP Error): {e}")
                    except httpx.RequestError as e:
                        logging.warning(f"[NRCS_NAM] Search failed for prefix '{prefix}' (Request Error): {e}")
                    except Exception as e:
                        logging.error(f"[NRCS_NAM] Unexpected error during search for prefix '{prefix}': {e}")

        except Exception as e:
            logging.error(f"[NRCS_NAM] General error during fetching: {e}")
            return []

        if not records:
            logging.warning("[NRCS_NAM] No records found. The portal might not have a public search function for drug registrations, or is inaccessible.")

        self.log(f"Total unique records fetched: {len(records)}")
        return records
