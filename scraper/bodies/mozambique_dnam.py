"""
Mozambique DNAM scraper — STUB (no accessible register found)

Regulator: DNAM (Direcção Nacional de Assistência Médica) under MISAU
Website: http://www.misau.gov.mz

Status: No accessible medicines register was found.
  - dnam.gov.mz: DNS does not resolve
  - misau.gov.mz: Homepage only, no medicine register links
  - Pharmadex (USAID/MSH): not deployed for Mozambique
  - MTAPS program (mtapsprogram.org): no public API

To unblock: contact MISAU directly, or check if Mozambique has
adopted Pharmadex through the MSH SIAPS programme. The East African
Community (EAC) may also have Mozambique data via regional databases.
"""

import logging
import sys

log = logging.getLogger("mozambique_dnam")


class MozambiqueDNAMScraper:
    body_code = "DNAM_MZ"
    country_code = "MZ"
    source_url = "http://www.misau.gov.mz"

    def fetch(self):
        log.warning(
            "[DNAM_MZ] Mozambique DNAM has no publicly accessible medicine register. "
            "Skipping. dnam.gov.mz does not resolve; misau.gov.mz has no register."
        )
        return []


def run(dry_run: bool = False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = MozambiqueDNAMScraper()
    scraper.fetch()


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
