import hashlib
import json
import logging
import os
from typing import Optional

import psycopg2
from psycopg2.extensions import connection

from base import RegistrationRecord


def get_conn() -> connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(url)


def compute_hash(record: RegistrationRecord) -> str:
    payload = {
        k: str(v)
        for k, v in record.__dict__.items()
        if k != "raw"
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()


def upsert(conn: connection, record: RegistrationRecord) -> bool:
    """
    Insert or update a registration record.
    Always bumps last_verified to confirm the record still exists in the source.
    Returns True if data changed (new record or hash changed), False if only last_verified updated.
    """
    h = compute_hash(record)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO registrations (
                inn, brand_name, country_code, registration_no, holder,
                local_agent, status, expiry_date, dosage_forms,
                source_url, source_type, product_type, raw_source_hash, last_verified
            ) VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, now())
            ON CONFLICT (country_code, registration_no)
            DO UPDATE SET
                last_verified   = now(),
                inn             = EXCLUDED.inn,
                brand_name      = EXCLUDED.brand_name,
                status          = EXCLUDED.status,
                expiry_date     = EXCLUDED.expiry_date,
                holder          = EXCLUDED.holder,
                local_agent     = EXCLUDED.local_agent,
                dosage_forms    = EXCLUDED.dosage_forms,
                source_url      = EXCLUDED.source_url,
                product_type    = EXCLUDED.product_type,
                raw_source_hash = EXCLUDED.raw_source_hash
            RETURNING id, (xmax = 0 OR raw_source_hash = %s) AS data_changed
        """, (
            record.inn, record.brand_name, record.country_code,
            record.registration_no or f"UNKNOWN-{h[:8]}",
            record.holder, record.local_agent,
            record.status, record.expiry_date, record.dosage_forms,
            record.source_url, record.source_type, record.product_type, h,
            h,
        ))
        row = cur.fetchone()
        return bool(row and row[1])


def update_last_scraped(conn: connection, country_code: str):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO regulatory_bodies (country_code, name, last_scraped)
            VALUES (%s, %s, now())
            ON CONFLICT (country_code) DO UPDATE SET last_scraped = now()
        """, (country_code, country_code))
    conn.commit()


def log_error(conn: connection, body_code: str, error: str):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO scrape_errors (body_code, error, created_at)
            VALUES (%s, %s, now())
        """, (body_code, error[:2000]))
    conn.commit()
