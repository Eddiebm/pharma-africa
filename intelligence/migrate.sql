-- ============================================================
-- Pharma Africa — Intelligence Layer Migration
-- Run once against Neon DB
-- ============================================================

-- WHO Essential Medicines List (seeded from CSV)
CREATE TABLE IF NOT EXISTS who_eml (
    id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    inn      text NOT NULL UNIQUE,
    atc_code text,
    category text
);

-- WHO Prequalification list (scraped from WHO)
CREATE TABLE IF NOT EXISTS who_prequalified (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    inn                   text NOT NULL,
    brand_name            text,
    manufacturer          text,
    country_of_manufacture text,
    dosage_form           text,
    strength              text,
    prequalification_date date,
    status                text NOT NULL DEFAULT 'qualified',
    source_url            text,
    raw                   jsonb NOT NULL DEFAULT '{}',
    scraped_at            timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_who_preq UNIQUE (inn, manufacturer, dosage_form, strength)
);

-- Intelligence signals
CREATE TABLE IF NOT EXISTS signals (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type            text NOT NULL,
    severity        text NOT NULL DEFAULT 'info',   -- 'critical' | 'warning' | 'info'
    country_code    char(2),
    inn             text,
    brand_name      text,
    registration_id uuid REFERENCES registrations(id) ON DELETE CASCADE,
    payload         jsonb NOT NULL DEFAULT '{}',
    first_seen      timestamptz NOT NULL DEFAULT now(),
    last_seen       timestamptz NOT NULL DEFAULT now(),
    resolved_at     timestamptz,
    notified_at     timestamptz
);

-- One active signal per type per registration
CREATE UNIQUE INDEX IF NOT EXISTS uq_signal_registration
    ON signals (type, registration_id)
    WHERE registration_id IS NOT NULL AND resolved_at IS NULL;

-- One active signal per type per (country, inn) for market-level signals
CREATE UNIQUE INDEX IF NOT EXISTS uq_signal_market
    ON signals (type, country_code, inn)
    WHERE registration_id IS NULL AND resolved_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_signals_type     ON signals (type);
CREATE INDEX IF NOT EXISTS idx_signals_severity ON signals (severity);
CREATE INDEX IF NOT EXISTS idx_signals_country  ON signals (country_code);
CREATE INDEX IF NOT EXISTS idx_signals_seen     ON signals (last_seen DESC);

-- Nightly intelligence briefs
CREATE TABLE IF NOT EXISTS intelligence_briefs (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_date     date NOT NULL UNIQUE,
    signals_count  int NOT NULL DEFAULT 0,
    new_count      int NOT NULL DEFAULT 0,
    expiry_count   int NOT NULL DEFAULT 0,
    critical_count int NOT NULL DEFAULT 0,
    body           text NOT NULL,
    model          text,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- Daily market snapshots for trend detection
CREATE TABLE IF NOT EXISTS market_snapshots (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date       date NOT NULL,
    country_code        char(2) NOT NULL,
    total_active        int NOT NULL DEFAULT 0,
    total_expired       int NOT NULL DEFAULT 0,
    expiring_30_days    int NOT NULL DEFAULT 0,
    new_last_24h        int NOT NULL DEFAULT 0,
    unique_holders      int NOT NULL DEFAULT 0,
    unique_inns         int NOT NULL DEFAULT 0,
    eml_coverage_pct    numeric(5,2),   -- % of WHO EML drugs registered here
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_snapshot UNIQUE (snapshot_date, country_code)
);

-- ============================================================
-- Views
-- ============================================================

CREATE OR REPLACE VIEW expiry_radar AS
SELECT
    r.id,
    trim(r.country_code::text)       AS country_code,
    r.inn,
    r.brand_name,
    r.registration_no,
    r.holder,
    r.expiry_date,
    r.status,
    r.expiry_date - current_date     AS days_to_expiry,
    CASE
        WHEN r.expiry_date - current_date <= 30 THEN 'critical'
        WHEN r.expiry_date - current_date <= 60 THEN 'warning'
        ELSE 'info'
    END                              AS severity
FROM registrations r
WHERE r.expiry_date IS NOT NULL
  AND r.status = 'active'
  AND r.expiry_date BETWEEN current_date AND current_date + 90
ORDER BY r.expiry_date;


CREATE OR REPLACE VIEW market_gaps AS
-- Drugs active in 3+ of our markets but missing from at least one
WITH all_countries AS (
    SELECT DISTINCT trim(country_code::text) AS cc FROM registrations WHERE status = 'active'
),
coverage AS (
    SELECT
        lower(trim(inn))                              AS inn_norm,
        array_agg(DISTINCT trim(country_code::text) ORDER BY trim(country_code::text)) AS present_in,
        count(DISTINCT country_code)                  AS market_count
    FROM registrations
    WHERE status = 'active' AND inn IS NOT NULL AND inn != ''
    GROUP BY lower(trim(inn))
    HAVING count(DISTINCT country_code) >= 3
),
total_markets AS (SELECT count(*) AS n FROM all_countries)
SELECT
    c.inn_norm                                              AS inn,
    c.market_count                                          AS markets_present,
    (SELECT n FROM total_markets) - c.market_count          AS markets_missing,
    c.present_in
FROM coverage c
ORDER BY c.market_count DESC;


CREATE OR REPLACE VIEW single_source_risk AS
-- Active drugs with exactly one holder in a country (supply concentration risk)
SELECT
    trim(r.country_code::text) AS country_code,
    r.inn,
    r.brand_name,
    r.holder,
    r.registration_no,
    r.expiry_date,
    r.status,
    CASE
        WHEN r.expiry_date IS NOT NULL AND r.expiry_date - current_date <= 60 THEN 'critical'
        ELSE 'warning'
    END AS severity
FROM registrations r
WHERE r.status = 'active'
  AND r.inn IS NOT NULL AND r.inn != ''
  AND (r.country_code, lower(trim(r.inn))) IN (
      SELECT country_code, lower(trim(inn))
      FROM registrations
      WHERE status = 'active' AND inn IS NOT NULL AND inn != ''
      GROUP BY country_code, lower(trim(inn))
      HAVING count(DISTINCT holder) = 1
         AND count(*) = 1      -- only one registration for this INN in this market
  )
ORDER BY severity DESC, r.country_code, r.inn;


CREATE OR REPLACE VIEW who_eml_coverage AS
-- For each country × EML drug, is it registered?
SELECT
    e.inn,
    e.atc_code,
    e.category,
    trim(c.cc::text)                                             AS country_code,
    bool_or(r.id IS NOT NULL)                                    AS is_registered,
    count(r.id)                                                  AS registration_count,
    max(r.status)                                                AS status
FROM who_eml e
CROSS JOIN (SELECT DISTINCT trim(country_code::text) AS cc FROM registrations) c
LEFT JOIN registrations r
    ON lower(trim(r.inn)) LIKE '%' || lower(trim(e.inn)) || '%'
    AND trim(r.country_code::text) = trim(c.cc::text)
    AND r.status = 'active'
GROUP BY e.inn, e.atc_code, e.category, c.cc
ORDER BY e.category, e.inn, c.cc;
