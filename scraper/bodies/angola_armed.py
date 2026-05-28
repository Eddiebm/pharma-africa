"""
Angola ARMED scraper — STUB (auth-gated)

ARMED (Agência Reguladora de Medicamentos e Tecnologias de Saúde)
Website: https://armed.gov.ao
Backend: https://armed-production-server.up.railway.app

Status: The backend API is auth-gated via Bearer token.
  - GET /medicamentos returns {"success":false,"medicamentos":[]}  (404)
  - All admin endpoints require a valid JWT from POST /auth/login-admin
  - No public-facing medicine search endpoint was found

To unblock: obtain valid admin credentials from ARMED, or register
a user account and reverse-engineer the token flow.
"""

import logging
import sys

log = logging.getLogger("angola_armed")


class AngolaARMEDScraper:
    body_code = "ARMED_AO"
    country_code = "AO"
    source_url = "https://armed.gov.ao"

    def fetch(self):
        log.warning(
            "[ARMED_AO] Angola ARMED is auth-gated — no public medicine register API. "
            "Skipping. To activate: add ARMED_API_TOKEN to .env."
        )
        return []


def run(dry_run: bool = False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = AngolaARMEDScraper()
    scraper.fetch()


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
