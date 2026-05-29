"""
Test harness — runs a generated scraper in dry-run mode and validates output.
"""
import subprocess
import sys
import json
import tempfile
import os
from pathlib import Path

SCRAPER_DIR = Path(__file__).parent.parent / "scraper"
VENV_PYTHON = Path(__file__).parent.parent / ".venv" / "bin" / "python3"

TEST_SCRIPT = """
import sys, json, os
sys.path.insert(0, '{scraper_dir}')
sys.path.insert(0, '{bodies_dir}')
os.chdir('{scraper_dir}')

import importlib.util
spec = importlib.util.spec_from_file_location("body", "{body_file}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Find the scraper class
scraper_cls = None
for name in dir(mod):
    obj = getattr(mod, name)
    try:
        from base import BaseRegulatoryScraper
        if isinstance(obj, type) and issubclass(obj, BaseRegulatoryScraper) and obj is not BaseRegulatoryScraper:
            scraper_cls = obj
            break
    except Exception:
        pass

if not scraper_cls:
    print(json.dumps({{"ok": False, "error": "No scraper class found", "count": 0}}))
    sys.exit(1)

try:
    scraper = scraper_cls()
    records = scraper.fetch()
    print(json.dumps({{"ok": True, "count": len(records), "sample": [
        {{"inn": r.inn, "brand": r.brand_name, "country": r.country_code}}
        for r in records[:3]
    ]}}))
except Exception as e:
    print(json.dumps({{"ok": False, "error": str(e), "count": 0}}))
    sys.exit(1)
"""

def test_scraper(body_file: Path, env: dict | None = None) -> dict:
    """
    Run the scraper at body_file and return result dict:
    {"ok": bool, "count": int, "sample": [...], "error": str|None}
    """
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

    script = TEST_SCRIPT.format(
        scraper_dir=str(SCRAPER_DIR),
        bodies_dir=str(SCRAPER_DIR / "bodies"),
        body_file=str(body_file),
    )

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    try:
        result = subprocess.run(
            [python, "-c", script],
            capture_output=True, text=True,
            timeout=300, env=run_env,
            cwd=str(SCRAPER_DIR),
        )
        # Find last JSON line
        for line in reversed(result.stdout.strip().splitlines()):
            try:
                return json.loads(line)
            except Exception:
                continue
        return {"ok": False, "error": result.stderr[-1000:] or "no output", "count": 0}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout after 300s", "count": 0}
    except Exception as e:
        return {"ok": False, "error": str(e), "count": 0}
