-- Blog posts table for AfriReg auto-generated content
CREATE TABLE IF NOT EXISTS blog_posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text UNIQUE NOT NULL,
  title text NOT NULL,
  description text NOT NULL,
  content text NOT NULL,
  category text NOT NULL CHECK (category IN ('expiry-watch', 'new-registrations', 'generic-opportunities', 'market-entry')),
  country_code text,
  published_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS blog_posts_published_at_idx ON blog_posts (published_at DESC);
CREATE INDEX IF NOT EXISTS blog_posts_category_idx ON blog_posts (category);
CREATE INDEX IF NOT EXISTS blog_posts_slug_idx ON blog_posts (slug);

-- signals table processed column (for IntelAgent)
ALTER TABLE signals ADD COLUMN IF NOT EXISTS processed boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS signals_processed_idx ON signals (processed) WHERE NOT processed;
