"""
Intelligence Run Orchestrator
------------------------------
Sequence: detect signals → generate brief → (optional) push to Telegram
Run nightly after all scrapers complete.

Usage:
  python run.py              # full run
  python run.py --detect-only
  python run.py --brief-only
"""

import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run")

# Ensure intelligence dir is in path
sys.path.insert(0, os.path.dirname(__file__))
import detect
import brief as brief_mod


def push_telegram(text: str):
    """Push brief summary to Telegram via Hermes empire bus (optional)."""
    import httpx
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.info("TELEGRAM_BOT_TOKEN/CHAT_ID not set — skipping Telegram push")
        return
    # Send first 4000 chars (Telegram message limit)
    snippet = text[:4000]
    httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": snippet, "parse_mode": "Markdown"},
        timeout=15,
    )
    log.info("Brief pushed to Telegram")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--detect-only", action="store_true")
    parser.add_argument("--brief-only",  action="store_true")
    parser.add_argument("--telegram",    action="store_true", help="Push brief to Telegram")
    args = parser.parse_args()

    if not args.brief_only:
        log.info("=== Phase 1: Signal Detection ===")
        result = detect.run()
        log.info(f"Signals: {result}")

    if not args.detect_only:
        log.info("=== Phase 2: Brief Generation ===")
        brief_text = brief_mod.run()
        if brief_text and args.telegram:
            push_telegram(brief_text)


if __name__ == "__main__":
    main()
