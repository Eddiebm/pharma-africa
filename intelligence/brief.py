"""
Intelligence Brief Generator
-----------------------------
Pulls today's signals from the DB, synthesises them with Gemini via OpenRouter,
and writes a structured markdown brief back to the intelligence_briefs table.
"""

import os
import sys
import json
import logging
from datetime import date

import httpx
import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("brief")

DB_URL = os.environ.get("DATABASE_URL")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "google/gemini-2.5-flash"

if not DB_URL:
    sys.exit("DATABASE_URL not set")
if not OPENROUTER_API_KEY:
    sys.exit("OPENROUTER_API_KEY not set")


def get_conn():
    return psycopg2.connect(DB_URL)


def load_signal_summary(conn) -> dict:
    today = date.today()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

        # Critical expiry alerts
        cur.execute("""
            SELECT country_code, inn, brand_name, payload->>'holder'        AS holder,
                   payload->>'days_to_expiry' AS days,
                   payload->>'expiry_date'    AS expiry_date
            FROM signals
            WHERE type = 'expiry_alert' AND severity = 'critical'
              AND resolved_at IS NULL
            ORDER BY (payload->>'days_to_expiry')::int
            LIMIT 20
        """)
        critical_expiry = cur.fetchall()

        # Warning expiry
        cur.execute("""
            SELECT country_code, inn, brand_name, payload->>'holder' AS holder,
                   payload->>'days_to_expiry' AS days
            FROM signals
            WHERE type = 'expiry_alert' AND severity = 'warning'
              AND resolved_at IS NULL
            ORDER BY (payload->>'days_to_expiry')::int
            LIMIT 20
        """)
        warning_expiry = cur.fetchall()

        # New registrations (last 24h)
        cur.execute("""
            SELECT country_code, inn, brand_name, payload->>'holder' AS holder
            FROM signals
            WHERE type = 'new_registration'
              AND resolved_at IS NULL
              AND first_seen >= now() - interval '25 hours'
            ORDER BY country_code, inn
            LIMIT 30
        """)
        new_regs = cur.fetchall()

        # Single source risks
        cur.execute("""
            SELECT country_code, inn, brand_name,
                   payload->>'holder' AS holder,
                   payload->>'expiry_date' AS expiry_date
            FROM signals
            WHERE type = 'single_source' AND severity = 'critical'
              AND resolved_at IS NULL
            LIMIT 15
        """)
        single_critical = cur.fetchall()

        # Market gaps (top by market count)
        cur.execute("""
            SELECT inn, country_code AS missing_from,
                   payload->>'market_count' AS present_in_n,
                   payload->>'present_in'   AS present_in
            FROM signals
            WHERE type = 'market_gap' AND resolved_at IS NULL
            ORDER BY (payload->>'market_count')::int DESC
            LIMIT 15
        """)
        gaps = cur.fetchall()

        # EML gaps summary by country
        cur.execute("""
            SELECT country_code, count(*) AS missing_eml_count
            FROM signals
            WHERE type = 'eml_gap' AND resolved_at IS NULL
            GROUP BY country_code
            ORDER BY missing_eml_count DESC
        """)
        eml_by_country = cur.fetchall()

        # WHO prequalified medicines not registered in any African market
        cur.execute("""
            SELECT inn, payload->>'holder' AS holder
            FROM signals
            WHERE type = 'who_unregistered' AND resolved_at IS NULL
            ORDER BY inn
            LIMIT 20
        """)
        who_unregistered = cur.fetchall()

        # Market snapshot
        cur.execute("""
            SELECT country_code, total_active, total_expired,
                   expiring_30_days, new_last_24h, unique_holders, unique_inns
            FROM market_snapshots
            WHERE snapshot_date = current_date
            ORDER BY total_active DESC
        """)
        snapshots = cur.fetchall()

        # Signal counts
        cur.execute("""
            SELECT type, severity, count(*) AS n
            FROM signals WHERE resolved_at IS NULL
            GROUP BY type, severity ORDER BY type, severity
        """)
        counts = cur.fetchall()

    return {
        "date": str(today),
        "critical_expiry": [dict(r) for r in critical_expiry],
        "warning_expiry":  [dict(r) for r in warning_expiry],
        "new_registrations": [dict(r) for r in new_regs],
        "single_source_critical": [dict(r) for r in single_critical],
        "market_gaps_top": [dict(r) for r in gaps],
        "eml_gaps_by_country": [dict(r) for r in eml_by_country],
        "who_unregistered": [dict(r) for r in who_unregistered],
        "market_snapshots": [dict(r) for r in snapshots],
        "signal_counts": [dict(r) for r in counts],
    }


def build_prompt(data: dict) -> str:
    snapshots_text = "\n".join(
        f"  {s['country_code']}: {s['total_active']} active | {s['expiring_30_days']} expiring in 30d | "
        f"{s['new_last_24h']} new | {s['unique_holders']} holders | {s['unique_inns']} unique INNs"
        for s in data["market_snapshots"]
    )

    critical_text = "\n".join(
        f"  [{r['country_code']}] {r['inn']} ({r['brand_name'] or 'no brand'}) — "
        f"{r['days']} days | holder: {r['holder']} | expires: {r['expiry_date']}"
        for r in data["critical_expiry"]
    ) or "  None"

    warning_text = "\n".join(
        f"  [{r['country_code']}] {r['inn']} — {r['days']} days"
        for r in data["warning_expiry"]
    ) or "  None"

    new_text = "\n".join(
        f"  [{r['country_code']}] {r['inn']} ({r['brand_name'] or ''}) — {r['holder'] or 'unknown holder'}"
        for r in data["new_registrations"]
    ) or "  None"

    single_text = "\n".join(
        f"  [{r['country_code']}] {r['inn']} — sole holder: {r['holder']} | expiry: {r['expiry_date']}"
        for r in data["single_source_critical"]
    ) or "  None"

    gaps_text = "\n".join(
        f"  {r['inn']} — in {r['present_in_n']} markets ({r['present_in']}) but NOT in {r['missing_from']}"
        for r in data["market_gaps_top"]
    ) or "  None"

    eml_text = "\n".join(
        f"  {r['country_code']}: {r['missing_eml_count']} WHO essential medicines not registered"
        for r in data["eml_gaps_by_country"]
    ) or "  None"

    who_unreg_text = "\n".join(
        f"  {r['inn']} — holder: {r['holder'] or 'unknown'}"
        for r in data["who_unregistered"]
    ) or "  None"

    return f"""You are a senior pharmaceutical market intelligence analyst specialising in sub-Saharan and North Africa.

Today is {data['date']}. Below is structured signal data from a pharma regulatory database covering {len(data['market_snapshots'])} African markets. Write a concise, professional intelligence brief.

=== MARKET OVERVIEW ===
{snapshots_text}

=== CRITICAL EXPIRY ALERTS (< 30 days) ===
{critical_text}

=== WARNING EXPIRY ALERTS (30-60 days) ===
{warning_text}

=== NEW REGISTRATIONS (last 24h) ===
{new_text}

=== CRITICAL SINGLE-SOURCE SUPPLY RISK ===
{single_text}

=== TOP MARKET GAPS (registered in multiple markets but absent here) ===
{gaps_text}

=== WHO ESSENTIAL MEDICINES GAPS BY COUNTRY ===
{eml_text}

=== WHO-PREQUALIFIED MEDICINES NOT REGISTERED IN ANY AFRICAN MARKET ===
{who_unreg_text}

Write a structured intelligence brief in markdown with these sections:
1. **Executive Summary** (3-5 bullet points — most important developments)
2. **Critical Alerts** (items needing immediate attention: expiries <30 days, critical supply risks)
3. **Market Intelligence** (patterns, gaps, new entrant activity, notable trends)
4. **Predicted Developments** (what these signals suggest will happen next — be specific)
5. **Watch List** (top 5 items to monitor closely in the next 7 days)

Be specific. Name drugs, countries, companies. Identify patterns across markets. Make predictions. This brief goes to pharma executives and regulators — they need actionable intelligence, not summaries of what they already see in the data.
"""


def generate_brief(prompt: str) -> str:
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def save_brief(conn, data: dict, brief_text: str):
    critical = len(data["critical_expiry"])
    new_count = len(data["new_registrations"])
    total_signals = sum(r["n"] for r in data["signal_counts"])
    expiry_count = sum(r["n"] for r in data["signal_counts"] if r["type"] == "expiry_alert")

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO intelligence_briefs
                (brief_date, signals_count, new_count, expiry_count, critical_count, body, model)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (brief_date) DO UPDATE SET
                signals_count  = EXCLUDED.signals_count,
                new_count      = EXCLUDED.new_count,
                expiry_count   = EXCLUDED.expiry_count,
                critical_count = EXCLUDED.critical_count,
                body           = EXCLUDED.body,
                model          = EXCLUDED.model,
                created_at     = now()
        """, (
            data["date"], total_signals, new_count, expiry_count, critical, brief_text, MODEL
        ))
    conn.commit()
    log.info(f"Brief saved for {data['date']}")


def run():
    conn = get_conn()
    try:
        log.info("Loading signal summary...")
        data = load_signal_summary(conn)

        if not data["market_snapshots"]:
            log.warning("No market snapshots found — run detect.py first")
            return

        log.info(f"Building brief for {data['date']} — "
                 f"{len(data['critical_expiry'])} critical, "
                 f"{len(data['new_registrations'])} new regs, "
                 f"{len(data['market_gaps_top'])} gap signals")

        prompt = build_prompt(data)
        log.info("Calling Gemini via OpenRouter...")
        brief_text = generate_brief(prompt)

        save_brief(conn, data, brief_text)

        print("\n" + "="*60)
        print(brief_text)
        print("="*60)
        return brief_text

    finally:
        conn.close()


if __name__ == "__main__":
    run()
