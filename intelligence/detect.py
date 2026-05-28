"""
Signal Detection Engine
-----------------------
Scans the registrations DB and fires intelligence signals into the signals table.

Signal types:
  expiry_alert       — active registration expiring within 90 days
  single_source      — only one holder for an INN in a market (supply risk)
  market_gap         — drug in 3+ markets but absent from a specific country
  new_registration   — registration created in last 25 hours (scrape cycle gap)
  eml_gap            — WHO Essential Medicine with zero registrations in a country
  who_unregistered   — WHO-prequalified product not found in any African market
"""

import os
import sys
import logging
import json
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("detect")

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    sys.exit("DATABASE_URL not set")


def get_conn():
    return psycopg2.connect(
        DB_URL,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
        options="-c statement_timeout=600000",  # 10 min — long-running detection queries
    )


def upsert_signal(cur, *, type_, severity, country_code=None, inn=None,
                  brand_name=None, registration_id=None, payload=None):
    """Insert or refresh a signal. Returns True if new, False if refreshed."""
    payload_json = json.dumps(payload or {})

    if registration_id:
        cur.execute("""
            INSERT INTO signals
                (type, severity, country_code, inn, brand_name, registration_id, payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (type, registration_id)
                WHERE registration_id IS NOT NULL AND resolved_at IS NULL
            DO UPDATE SET
                severity   = EXCLUDED.severity,
                last_seen  = now(),
                payload    = EXCLUDED.payload
            RETURNING (xmax = 0) AS is_new
        """, (type_, severity, country_code, inn, brand_name, registration_id, payload_json))
    else:
        cur.execute("""
            INSERT INTO signals
                (type, severity, country_code, inn, brand_name, payload)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (type, country_code, inn)
                WHERE registration_id IS NULL AND resolved_at IS NULL
            DO UPDATE SET
                severity  = EXCLUDED.severity,
                last_seen = now(),
                payload   = EXCLUDED.payload
            RETURNING (xmax = 0) AS is_new
        """, (type_, severity, country_code, inn, brand_name, payload_json))

    row = cur.fetchone()
    return row[0] if row else False


def resolve_stale_signals(cur):
    """Resolve expiry signals for registrations that are no longer expiring within 90 days."""
    cur.execute("""
        UPDATE signals s SET resolved_at = now()
        FROM registrations r
        WHERE s.registration_id = r.id
          AND s.type = 'expiry_alert'
          AND s.resolved_at IS NULL
          AND (
              r.expiry_date IS NULL
              OR r.expiry_date > current_date + 90
              OR r.status != 'active'
          )
    """)
    return cur.rowcount


def detect_expiry_alerts(cur) -> dict:
    cur.execute("""
        SELECT id, trim(country_code::text) AS cc, inn, brand_name, holder,
               expiry_date,
               expiry_date - current_date AS days_left
        FROM registrations
        WHERE status = 'active'
          AND expiry_date IS NOT NULL
          AND expiry_date BETWEEN current_date AND current_date + 90
    """)
    rows = cur.fetchall()
    counts = {"critical": 0, "warning": 0, "info": 0}
    for row in rows:
        rid, cc, inn, brand, holder, exp, days = row
        if days <= 30:
            sev = "critical"
        elif days <= 60:
            sev = "warning"
        else:
            sev = "info"
        upsert_signal(cur,
            type_="expiry_alert", severity=sev,
            country_code=cc, inn=inn, brand_name=brand,
            registration_id=rid,
            payload={"days_to_expiry": days, "expiry_date": str(exp), "holder": holder}
        )
        counts[sev] += 1
    log.info(f"[expiry_alert] critical={counts['critical']} warning={counts['warning']} info={counts['info']}")
    return counts


def detect_single_source(cur) -> int:
    cur.execute("""
        WITH solo AS (
            SELECT trim(country_code::text) AS cc, lower(trim(inn)) AS inn_norm
            FROM registrations
            WHERE status = 'active' AND inn IS NOT NULL AND inn != ''
            GROUP BY trim(country_code::text), lower(trim(inn))
            HAVING count(DISTINCT holder) = 1 AND count(*) = 1
        )
        SELECT r.id, trim(r.country_code::text) AS cc, r.inn, r.brand_name,
               r.holder, r.expiry_date
        FROM registrations r
        JOIN solo s ON trim(r.country_code::text) = s.cc
                   AND lower(trim(r.inn)) = s.inn_norm
        WHERE r.status = 'active' AND r.inn IS NOT NULL AND r.inn != ''
    """)
    rows = cur.fetchall()
    n = 0
    for row in rows:
        rid, cc, inn, brand, holder, exp = row
        sev = "critical" if (exp and (exp - datetime.now(timezone.utc).date()).days <= 60) else "warning"
        upsert_signal(cur,
            type_="single_source", severity=sev,
            country_code=cc, inn=inn, brand_name=brand,
            registration_id=rid,
            payload={"holder": holder, "country": cc,
                     "expiry_date": str(exp) if exp else None}
        )
        n += 1
    log.info(f"[single_source] {n} signals")
    return n


def detect_who_unregistered(cur) -> int:
    """WHO-prequalified FPPs with no match in any African country registration.
    Python-side matching avoids the LIKE '%inn%' full-table-scan anti-pattern.
    """
    # Load all African (non-WW) active INN norms in one pass
    cur.execute("""
        SELECT DISTINCT lower(trim(inn)) AS inn_norm
        FROM registrations
        WHERE status = 'active' AND inn IS NOT NULL AND inn != '' AND country_code != 'WW'
    """)
    african_inns: set[str] = {row[0] for row in cur.fetchall()}

    # Load WHO-PQ registrations
    cur.execute("""
        SELECT DISTINCT lower(trim(inn)) AS inn_norm, inn, holder
        FROM registrations
        WHERE country_code = 'WW' AND status = 'active'
          AND inn IS NOT NULL AND inn != ''
    """)
    ww_rows = cur.fetchall()

    n = 0
    for inn_norm, inn, holder in ww_rows:
        # Found if any African INN contains this WHO INN as a substring
        found = any(inn_norm in african_inn for african_inn in african_inns)
        if not found:
            upsert_signal(cur,
                type_="who_unregistered", severity="warning",
                country_code="WW", inn=inn,
                registration_id=None,
                payload={"holder": holder, "source": "WHO Prequalification"}
            )
            n += 1

    log.info(f"[who_unregistered] {n} signals")
    return n


def detect_market_gaps(cur) -> int:
    """Flag drugs present in 3+ African markets but absent from others we cover."""
    cur.execute("""
        SELECT DISTINCT trim(country_code::text) AS cc
        FROM registrations
        WHERE status = 'active' AND country_code != 'WW'
    """)
    all_countries = {row[0] for row in cur.fetchall()}

    cur.execute("""
        SELECT lower(trim(inn)) AS inn_norm,
               array_agg(DISTINCT trim(country_code::text)) AS countries,
               count(DISTINCT country_code) AS n
        FROM registrations
        WHERE status = 'active' AND inn IS NOT NULL AND inn != ''
          AND country_code != 'WW'
        GROUP BY lower(trim(inn))
        HAVING count(DISTINCT country_code) >= 3
    """)
    rows = cur.fetchall()
    n = 0
    for inn_norm, countries, _ in rows:
        missing = all_countries - set(countries)
        if not missing:
            continue
        for missing_cc in missing:
            upsert_signal(cur,
                type_="market_gap", severity="info",
                country_code=missing_cc, inn=inn_norm,
                registration_id=None,
                payload={"present_in": sorted(countries),
                         "missing_from": missing_cc,
                         "market_count": len(countries)}
            )
            n += 1
    log.info(f"[market_gap] {n} signals")
    return n


def detect_new_registrations(cur) -> int:
    cur.execute("""
        SELECT id, trim(country_code::text) AS cc, inn, brand_name, holder, created_at
        FROM registrations
        WHERE created_at >= now() - interval '25 hours'
    """)
    rows = cur.fetchall()
    n = 0
    for row in rows:
        rid, cc, inn, brand, holder, created = row
        upsert_signal(cur,
            type_="new_registration", severity="info",
            country_code=cc, inn=inn, brand_name=brand,
            registration_id=rid,
            payload={"holder": holder, "created_at": str(created)}
        )
        n += 1
    log.info(f"[new_registration] {n} signals")
    return n


def detect_eml_gaps(cur) -> int:
    """EML drugs with zero active registrations in a country we cover.
    Python-side matching avoids the LIKE '%inn%' full-table-scan anti-pattern.
    """
    # Load all active INNs by country in one pass
    cur.execute("""
        SELECT DISTINCT trim(country_code::text) AS cc, lower(trim(inn)) AS inn_norm
        FROM registrations
        WHERE status = 'active' AND inn IS NOT NULL AND inn != '' AND country_code != 'WW'
    """)
    country_inns: dict[str, set[str]] = {}
    for cc, inn_norm in cur.fetchall():
        country_inns.setdefault(cc, set()).add(inn_norm)

    all_countries = set(country_inns.keys())

    # Load WHO EML drugs
    cur.execute("SELECT inn, category FROM who_eml")
    eml_drugs = cur.fetchall()

    n = 0
    for eml_inn, category in eml_drugs:
        eml_norm = eml_inn.lower().strip()
        for cc in all_countries:
            inns_in_country = country_inns.get(cc, set())
            # Check if any registered INN contains the EML INN as a substring
            found = any(eml_norm in reg_inn for reg_inn in inns_in_country)
            if not found:
                upsert_signal(cur,
                    type_="eml_gap", severity="warning",
                    country_code=cc, inn=eml_inn,
                    registration_id=None,
                    payload={"category": category, "source": "WHO EML 23rd edition"}
                )
                n += 1

    log.info(f"[eml_gap] {n} signals")
    return n


def take_market_snapshot(cur):
    cur.execute("""
        INSERT INTO market_snapshots
            (snapshot_date, country_code, total_active, total_expired,
             expiring_30_days, new_last_24h, unique_holders, unique_inns)
        SELECT
            current_date,
            trim(country_code::text),
            count(*) FILTER (WHERE status = 'active'),
            count(*) FILTER (WHERE status = 'expired'),
            count(*) FILTER (WHERE status = 'active'
                              AND expiry_date BETWEEN current_date AND current_date + 30),
            count(*) FILTER (WHERE created_at >= now() - interval '25 hours'),
            count(DISTINCT holder) FILTER (WHERE status = 'active'),
            count(DISTINCT lower(trim(inn))) FILTER (WHERE status = 'active')
        FROM registrations
        GROUP BY trim(country_code::text)
        ON CONFLICT (snapshot_date, country_code) DO UPDATE SET
            total_active     = EXCLUDED.total_active,
            total_expired    = EXCLUDED.total_expired,
            expiring_30_days = EXCLUDED.expiring_30_days,
            new_last_24h     = EXCLUDED.new_last_24h,
            unique_holders   = EXCLUDED.unique_holders,
            unique_inns      = EXCLUDED.unique_inns
    """)
    log.info(f"[snapshot] {cur.rowcount} market snapshots recorded")


def _run_step(fn, *args, max_retries: int = 3):
    """Execute a detection step with its own connection — prevents timeout cascade.
    Retries on transient SSL/network errors with a fresh connection each time.
    """
    import time as _time
    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                result = fn(cur, *args)
            conn.commit()
            return result
        except Exception as e:
            err = str(e)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            if attempt < max_retries and ("timed out" in err.lower() or "ssl" in err.lower() or "connection" in err.lower()):
                wait = 10 * attempt
                log.warning(f"[{fn.__name__}] attempt {attempt} failed: {e} — retrying in {wait}s")
                _time.sleep(wait)
                continue
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


def run():
    log.info("=== Signal detection starting ===")

    # Resolve stale signals
    stale = _run_step(resolve_stale_signals)
    log.info(f"Resolved {stale} stale expiry signals")

    expiry    = _run_step(detect_expiry_alerts)
    single    = _run_step(detect_single_source)
    gaps      = _run_step(detect_market_gaps)
    new_reg   = _run_step(detect_new_registrations)
    eml       = _run_step(detect_eml_gaps)
    who_unreg = _run_step(detect_who_unregistered)

    # Snapshot uses its own connection too
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            take_market_snapshot(cur)
        conn.commit()
    finally:
        conn.close()

    total = expiry["critical"] + expiry["warning"] + expiry["info"] + single + gaps + new_reg + eml + who_unreg
    log.info(f"=== Done | total signals upserted: {total} ===")
    return {
        "expiry_critical":   expiry["critical"],
        "expiry_warning":    expiry["warning"],
        "expiry_info":       expiry["info"],
        "single_source":     single,
        "market_gaps":       gaps,
        "new_registrations": new_reg,
        "eml_gaps":          eml,
        "who_unregistered":  who_unreg,
        "total":             total,
    }


if __name__ == "__main__":
    result = run()
    print(result)
