"""
Main runner — executes all enabled scrapers and writes to Neon.
Usage:
  python runner.py                  # run all scrapers
  python runner.py --body SAHPRA    # run a single body
  python runner.py --dry-run        # fetch only, no DB writes
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

import db
from base import RegistrationRecord
from bodies.sahpra       import SAHPRAScraper
from bodies.nafdac       import NAFDACScraper
from bodies.ppb_kenya    import KenyaPPBScraper
from bodies.ghana_fda    import GhanaFDAScraper
from bodies.rwanda_rda   import RwandaRDAScraper
from bodies.uganda_nda   import UgandaNDAScraper
from bodies.tanzania_tmda import TanzaniaTMDAScraper
from bodies.morocco_dmp  import MoroccoDMPScraper
from bodies.malawi_pmra  import MalawiPMRAScraper
from bodies.egypt_eda          import EgyptEDAScraper
from bodies.cote_divoire_airp  import CoteDIvoireAIRPScraper
from bodies.tunisia_dpm        import TunisiaDPMScraper
from bodies.madagascar_amm     import MadagascarAMMScraper
from bodies.senegal_arp        import SenegalARPScraper
from bodies.who_prequalified   import WHOPrequalifiedScraper
from bodies.angola_armed       import AngolaARMEDScraper
from bodies.mozambique_dnam    import MozambiqueDNAMScraper
from bodies.zimbabwe_mcaz      import ZimbabweMCAZScraper
from bodies.zamra_zambia       import ZAMRAZambiaScraper
from bodies.pcpb_kenya         import PCPBKenyaScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

ALL_SCRAPERS = [
    SAHPRAScraper(),
    NAFDACScraper(),
    KenyaPPBScraper(),
    GhanaFDAScraper(),
    RwandaRDAScraper(),
    UgandaNDAScraper(),
    TanzaniaTMDAScraper(),
    MoroccoDMPScraper(),
    MalawiPMRAScraper(),
    EgyptEDAScraper(),
    CoteDIvoireAIRPScraper(),
    TunisiaDPMScraper(),
    MadagascarAMMScraper(),
    SenegalARPScraper(),
    WHOPrequalifiedScraper(),
    AngolaARMEDScraper(),
    MozambiqueDNAMScraper(),
    ZimbabweMCAZScraper(),
    ZAMRAZambiaScraper(),
    PCPBKenyaScraper(),
]


def run_scraper(scraper, conn, dry_run: bool) -> dict:
    start = time.time()
    result = {
        "body": scraper.body_code,
        "fetched": 0,
        "written": 0,
        "skipped": 0,
        "error": None,
        "duration_s": 0,
    }

    try:
        records: list[RegistrationRecord] = scraper.fetch()
        result["fetched"] = len(records)

        if not dry_run and records:
            for record in records:
                try:
                    wrote = db.upsert(conn, record)
                    if wrote:
                        result["written"] += 1
                    else:
                        result["skipped"] += 1
                except Exception as e:
                    logging.error(f"[{scraper.body_code}] Upsert failed: {e}")
                    result["error"] = str(e)
                    conn.rollback()
                    break
            conn.commit()
            if not result["error"]:
                db.update_last_scraped(conn, scraper.country_code)

    except Exception as e:
        result["error"] = str(e)
        logging.error(f"[{scraper.body_code}] Scraper failed: {e}", exc_info=True)
        if conn:
            try:
                db.log_error(conn, scraper.body_code, str(e))
            except Exception:
                pass

    result["duration_s"] = round(time.time() - start, 1)
    return result


def main():
    parser = argparse.ArgumentParser(description="African pharma regulatory scraper")
    parser.add_argument("--body", help="Run a single scraper by body_code (e.g. SAHPRA)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only — no DB writes")
    args = parser.parse_args()

    scrapers = ALL_SCRAPERS
    if args.body:
        scrapers = [s for s in ALL_SCRAPERS if s.body_code == args.body.upper()]
        if not scrapers:
            logging.error(f"Unknown body: {args.body}. Valid: {[s.body_code for s in ALL_SCRAPERS]}")
            sys.exit(1)

    logging.info(f"Running {len(scrapers)} scraper(s) — dry_run={args.dry_run}")

    results = []
    for scraper in scrapers:
        logging.info(f"--- {scraper.body_code} ---")
        # Fresh connection per scraper so long-running fetches don't timeout
        conn = None
        if not args.dry_run:
            conn = db.get_conn()
        result = run_scraper(scraper, conn, args.dry_run)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        results.append(result)
        status = "ERROR" if result["error"] else "OK"
        logging.info(
            f"[{scraper.body_code}] {status} | "
            f"fetched={result['fetched']} written={result['written']} "
            f"skipped={result['skipped']} time={result['duration_s']}s"
        )

    total_fetched = sum(r["fetched"] for r in results)
    total_written = sum(r["written"] for r in results)
    errors        = [r for r in results if r["error"]]
    logging.info(
        f"=== DONE | fetched={total_fetched} written={total_written} "
        f"errors={len(errors)} ==="
    )
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
