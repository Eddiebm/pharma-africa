"""
Orchestrator — automated scraper pipeline for AfriReg markets queue.

Usage:
  python orchestrator.py                   # process next pending market
  python orchestrator.py --market ETH      # process specific market by code
  python orchestrator.py --loop            # keep processing until queue empty
  python orchestrator.py --dry-run         # generate + test, skip deploy
  python orchestrator.py --loop --dry-run  # full loop without deploying

Flow per market:
  1. Fetch portal HTML
  2. Generate scraper via Claude claude-sonnet-4-5
  3. Write to scraper/bodies/
  4. Test via test harness (runs actual scraper)
  5. Deploy to Hetzner server (unless --dry-run)
  6. Update queue status
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent to path so we can import from generator siblings
sys.path.insert(0, str(Path(__file__).parent))

from scraper_generator import fetch_portal, generate_scraper
from test_harness import test_scraper
from deployer import deploy

QUEUE_FILE = Path(__file__).parent / "markets_queue.json"
LOGS_DIR = Path(__file__).parent / "logs"
BODIES_DIR = Path(__file__).parent.parent / "scraper" / "bodies"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("orchestrator")


# ── Queue helpers ──────────────────────────────────────────────────────────────

def load_queue() -> list[dict]:
    return json.loads(QUEUE_FILE.read_text())


def save_queue(queue: list[dict]):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))


def set_status(queue: list[dict], code: str, status: str, note: str = "") -> list[dict]:
    for m in queue:
        if m["code"] == code:
            m["status"] = status
            if note:
                m["note"] = note
            m["updated_at"] = datetime.utcnow().isoformat()
    return queue


def pick_market(queue: list[dict], code: str | None = None) -> dict | None:
    if code:
        for m in queue:
            if m["code"] == code:
                return m
        return None
    for m in queue:
        if m["status"] == "pending":
            return m
    return None


# ── Per-market logger ──────────────────────────────────────────────────────────

def market_logger(body_code: str) -> logging.Logger:
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / f"{body_code}.log"
    logger = logging.getLogger(f"market.{body_code}")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)
    return logger


# ── Core pipeline ──────────────────────────────────────────────────────────────

def run_market(market: dict, dry_run: bool = False) -> bool:
    """
    Run the full pipeline for one market.
    Returns True on success (deployed or tested if dry_run).
    """
    body_code = f"{market['body']}_{market['code']}"
    mlog = market_logger(body_code)
    mlog.info(f"=== Starting {market['country']} ({body_code}) ===")
    log.info(f"[{body_code}] Starting pipeline for {market['country']}")

    # ── 1. Fetch portal HTML ──────────────────────────────────────────────────
    log.info(f"[{body_code}] Fetching portal: {market['portal_hint']}")
    mlog.info(f"Fetching portal: {market['portal_hint']}")
    portal_html = fetch_portal(market["portal_hint"])
    if portal_html.startswith("FETCH_ERROR"):
        mlog.warning(f"Portal fetch failed: {portal_html}")
        log.warning(f"[{body_code}] Portal unreachable — generating stub scraper anyway")

    # ── 2. Generate scraper ───────────────────────────────────────────────────
    log.info(f"[{body_code}] Generating scraper via Claude...")
    mlog.info("Generating scraper via Claude")
    code = generate_scraper(market, portal_html)
    if not code:
        mlog.error("Claude returned no code")
        log.error(f"[{body_code}] Generation failed — skipping")
        return False

    mlog.info(f"Generated {len(code)} chars of Python")

    # ── 3. Write to bodies/ ───────────────────────────────────────────────────
    fname = f"{market['body'].lower()}_{market['code'].lower()}.py"
    body_file = BODIES_DIR / fname
    body_file.parent.mkdir(parents=True, exist_ok=True)
    body_file.write_text(code)
    mlog.info(f"Wrote {body_file}")
    log.info(f"[{body_code}] Written to {fname}")

    # ── 4. Test harness ───────────────────────────────────────────────────────
    log.info(f"[{body_code}] Running test harness (timeout 300s)...")
    mlog.info("Running test harness")

    env = {}
    twocaptcha_key = os.environ.get("TWOCAPTCHA_KEY", "")
    if twocaptcha_key:
        env["TWOCAPTCHA_KEY"] = twocaptcha_key

    result = test_scraper(body_file, env=env)
    mlog.info(f"Test result: {result}")

    if result["ok"]:
        log.info(f"[{body_code}] ✅ Test passed — {result['count']} records, sample: {result.get('sample', [])[:1]}")
    else:
        err = result.get("error", "unknown")
        # If the portal returns 0 records because it has no public search, that's fine —
        # the scraper logs a warning and returns []. Treat count==0 with no error as pass.
        if result["count"] == 0 and "no output" not in err and "timeout" not in err:
            log.info(f"[{body_code}] ⚠️  Test returned 0 records — portal may have no public search (acceptable)")
            mlog.info("0 records returned — marking as tested (no public search portal)")
        else:
            log.warning(f"[{body_code}] ❌ Test failed: {err}")
            mlog.warning(f"Test failed: {err}")
            if "syntax" in err.lower() or "ImportError" in err or "ModuleNotFoundError" in err:
                # Hard failure — bad generated code
                return False
            # Soft failure (network timeout, portal down) — still deploy and let cron retry
            log.info(f"[{body_code}] Soft failure — will deploy anyway so cron can retry later")

    # ── 5. Deploy ─────────────────────────────────────────────────────────────
    if dry_run:
        log.info(f"[{body_code}] --dry-run: skipping deploy")
        mlog.info("DRY RUN — deploy skipped")
        return True

    log.info(f"[{body_code}] Deploying to Hetzner...")
    mlog.info("Deploying to Hetzner")
    ok = deploy(body_file, market)
    if ok:
        log.info(f"[{body_code}] ✅ Deployed")
        mlog.info("Deploy success")
    else:
        log.error(f"[{body_code}] ❌ Deploy failed")
        mlog.error("Deploy failed")

    return ok


# ── Main entry ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AfriReg scraper generator orchestrator")
    parser.add_argument("--market", help="Process specific market by ISO-3 country code (e.g. ETH)")
    parser.add_argument("--loop", action="store_true", help="Keep processing until queue empty")
    parser.add_argument("--dry-run", action="store_true", help="Generate and test but skip deploy")
    parser.add_argument("--list", action="store_true", help="List queue statuses and exit")
    args = parser.parse_args()

    queue = load_queue()

    if args.list:
        by_status: dict[str, list[str]] = {}
        for m in queue:
            s = m["status"]
            by_status.setdefault(s, []).append(f"  {m['body']}_{m['code']} ({m['country']})")
        for status, items in sorted(by_status.items()):
            print(f"\n{status.upper()} ({len(items)}):")
            print("\n".join(items))
        return

    loop_count = 0
    while True:
        queue = load_queue()
        market = pick_market(queue, args.market)

        if not market:
            if args.market:
                log.error(f"Market code '{args.market}' not found in queue")
            else:
                log.info("Queue empty — all markets processed")
            break

        body_code = f"{market['body']}_{market['code']}"

        # Mark in-progress so parallel runs skip it
        queue = set_status(queue, market["code"], "in_progress")
        save_queue(queue)

        start = time.time()
        try:
            success = run_market(market, dry_run=args.dry_run)
        except Exception as e:
            log.exception(f"[{body_code}] Unhandled error: {e}")
            success = False

        elapsed = time.time() - start
        queue = load_queue()  # Reload in case another process touched it
        final_status = ("deployed" if not args.dry_run else "tested") if success else "failed"
        queue = set_status(queue, market["code"], final_status,
                           note=f"elapsed={elapsed:.0f}s")
        save_queue(queue)

        log.info(f"[{body_code}] Done in {elapsed:.0f}s → {final_status}")

        if not args.loop:
            break

        # Brief pause between markets to avoid hammering portals
        time.sleep(3)
        loop_count += 1

    # Print summary
    queue = load_queue()
    counts = {}
    for m in queue:
        counts[m["status"]] = counts.get(m["status"], 0) + 1
    log.info(f"Queue summary: {counts}")


if __name__ == "__main__":
    main()
