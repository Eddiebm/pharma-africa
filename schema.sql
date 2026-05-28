-- African Pharma Regulatory Intelligence — schema
-- Run once against your Neon database:
--   psql $DATABASE_URL -f schema.sql

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- -----------------------------------------------------------------------
-- Canonical drug identity (INN-normalised)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inn          TEXT NOT NULL,
    brand_name   TEXT,
    atc_code     TEXT,
    manufacturer TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_inn
    ON products USING GIN (inn gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_brand
    ON products USING GIN (brand_name gin_trgm_ops);

-- Full-text search vector (kept in sync automatically)
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
    GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(inn, '') || ' ' || coalesce(brand_name, '') || ' ' || coalesce(manufacturer, '')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_products_fts
    ON products USING GIN (search_vector);

-- -----------------------------------------------------------------------
-- One row per country registration
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS registrations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id       UUID REFERENCES products (id) ON DELETE SET NULL,

    -- Core identity
    inn              TEXT NOT NULL DEFAULT '',
    brand_name       TEXT,
    country_code     CHAR(2) NOT NULL,
    registration_no  TEXT,

    -- Registration details
    holder           TEXT,
    local_agent      TEXT,
    status           TEXT NOT NULL DEFAULT 'unknown'
                         CHECK (status IN ('active','expired','suspended','pending','alert','unknown')),
    expiry_date      DATE,
    dosage_forms     TEXT[] NOT NULL DEFAULT '{}',

    -- Source tracking
    source_url       TEXT NOT NULL DEFAULT '',
    source_type      TEXT NOT NULL DEFAULT 'scrape'
                         CHECK (source_type IN ('scrape','document','manual','alert')),
    raw_source_hash  TEXT,
    last_verified    TIMESTAMPTZ NOT NULL DEFAULT now(),

    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Unique per country + registration number; falls back to inn + brand when no reg no
    CONSTRAINT uq_registration UNIQUE (country_code, registration_no)
);

CREATE INDEX IF NOT EXISTS idx_reg_country      ON registrations (country_code);
CREATE INDEX IF NOT EXISTS idx_reg_status       ON registrations (status);
CREATE INDEX IF NOT EXISTS idx_reg_expiry       ON registrations (expiry_date) WHERE expiry_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reg_inn          ON registrations USING GIN (inn gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_reg_brand        ON registrations USING GIN (brand_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_reg_product      ON registrations (product_id) WHERE product_id IS NOT NULL;

-- -----------------------------------------------------------------------
-- Regulatory body metadata per country
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regulatory_bodies (
    country_code   CHAR(2) PRIMARY KEY,
    name           TEXT NOT NULL,
    portal_url     TEXT,
    search_method  TEXT CHECK (search_method IN ('scrape','api','document','manual','partner')),
    language       TEXT,
    coverage_pct   INT CHECK (coverage_pct BETWEEN 0 AND 100),
    last_scraped   TIMESTAMPTZ,
    active         BOOLEAN NOT NULL DEFAULT true
);

INSERT INTO regulatory_bodies (country_code, name, portal_url, search_method, language, coverage_pct)
VALUES
    ('ZA', 'SAHPRA', 'https://medapps.sahpra.org.za:6006', 'scrape', 'en', 90),
    ('NG', 'NAFDAC', 'https://greenbook.nafdac.gov.ng',   'scrape', 'en', 70),
    ('KE', 'PPB',    'https://www.kenyalaw.org',          'document','en', 50),
    ('GH', 'FDA Ghana', 'https://fdaghana.gov.gh',        'scrape', 'en', 10),
    ('RW', 'RDA Rwanda', 'https://fda.gov.rw',            'scrape', 'en', 40)
ON CONFLICT (country_code) DO NOTHING;

-- -----------------------------------------------------------------------
-- Scraper error log
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scrape_errors (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    body_code  TEXT NOT NULL,
    error      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scrape_errors_body ON scrape_errors (body_code, created_at DESC);

-- -----------------------------------------------------------------------
-- Multi-tenant: pharma companies using the platform
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    email      TEXT,
    plan       TEXT NOT NULL DEFAULT 'trial' CHECK (plan IN ('trial','starter','pro','enterprise')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------
-- Portfolio: products a company wants tracked
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_items (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id     UUID NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    inn            TEXT NOT NULL,
    brand_name     TEXT,
    added_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, inn)
);

-- -----------------------------------------------------------------------
-- Alert rules per company
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alert_rules (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    trigger    TEXT NOT NULL CHECK (trigger IN (
                   'expiry_12m', 'expiry_6m', 'expiry_3m',
                   'status_change', 'new_competitor'
               )),
    email      TEXT NOT NULL,
    active     BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, trigger, email)
);

-- -----------------------------------------------------------------------
-- Alert send log (deduplication — don't re-alert within 30 days)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alert_sends (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    registration_id UUID REFERENCES registrations (id) ON DELETE CASCADE,
    trigger         TEXT NOT NULL,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, registration_id, trigger)
);
