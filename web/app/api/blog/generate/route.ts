export const runtime = "edge";

import { neon } from "@neondatabase/serverless";

const COUNTRIES: Record<string, string> = {
  ZA: "South Africa", NG: "Nigeria", KE: "Kenya", GH: "Ghana", RW: "Rwanda",
  TZ: "Tanzania", UG: "Uganda", ET: "Ethiopia", ZM: "Zambia", ZW: "Zimbabwe",
  MA: "Morocco", MW: "Malawi", EG: "Egypt", SN: "Senegal", CI: "Côte d'Ivoire",
  TN: "Tunisia",
};

const CATEGORIES = ["expiry-watch", "new-registrations", "generic-opportunities", "market-entry"] as const;
type Category = typeof CATEGORIES[number];

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").slice(0, 80).replace(/-$/, "");
}

function fmt(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

const SYSTEM_PROMPT = `You are a pharmaceutical regulatory intelligence analyst writing for AfriReg — a B2B data platform for African pharma markets.

Write a data-driven blog post. Return ONLY a JSON object with these exact keys:
{
  "title": "...",
  "description": "...",
  "content": "..."
}

Rules:
- title: concise, specific, SEO-optimized (include country name + year where relevant)
- description: 140-160 chars, for meta description, summarise the key insight
- content: valid HTML fragment only — no <html>/<head>/<body> tags
  - Use <h2> for section headings
  - Use <table class="data-table"> with <thead>/<tbody> for all tabular data
  - Use <p class="lead"> for the opening paragraph with the key statistic
  - Use <p> for body paragraphs
  - 700-1000 words total
  - Authoritative, data-driven, no fluff
  - End with a <p> about how AfriReg Pro helps regulatory teams automate this tracking
  - Do NOT repeat the title inside the content`;

export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (!secret || req.headers.get("authorization") !== `Bearer ${secret}`) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const dbUrl = process.env.DATABASE_URL;
  const openrouterKey = process.env.OPENROUTER_API_KEY;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });
  if (!openrouterKey) return Response.json({ error: "OPENROUTER_API_KEY not configured" }, { status: 503 });

  let body: { type: Category; country_code?: string };
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { type, country_code = "" } = body;
  if (!CATEGORIES.includes(type)) {
    return Response.json({ error: `type must be one of: ${CATEGORIES.join(", ")}` }, { status: 400 });
  }

  const sql = neon(dbUrl);
  const countryName = country_code ? (COUNTRIES[country_code] || country_code) : "Africa";
  const now = new Date();
  const monthYear = now.toLocaleDateString("en-GB", { month: "long", year: "numeric" });

  let rows: Record<string, unknown>[];
  let userPrompt: string;

  if (type === "expiry-watch") {
    rows = await sql`
      SELECT inn, brand_name, holder, expiry_date, registration_no, country_code
      FROM registrations
      WHERE status = 'active'
        AND expiry_date BETWEEN NOW() AND NOW() + INTERVAL '90 days'
        AND source_type != 'alert'
        AND (${country_code} = '' OR country_code = ${country_code})
      ORDER BY expiry_date ASC LIMIT 40
    `;
    const table = rows.map(r => `${r.brand_name || r.inn} (${r.inn}) | ${r.holder || "—"} | ${COUNTRIES[r.country_code as string] || r.country_code} | ${fmt(r.expiry_date as string)} | ${r.registration_no || "—"}`).join("\n");
    userPrompt = `Write a blog post titled something like "Pharmaceutical Registrations Expiring in ${countryName} — Next 90 Days (${monthYear})".

Data: ${rows.length} active registrations expiring in the next 90 days${country_code ? ` in ${countryName}` : " across Africa"}.

Drug | Holder | Country | Expiry Date | Reg No
${table}

Highlight the most critical expirations (key generics, essential medicines, large holders). Discuss the regulatory implications of letting registrations lapse.`;
  } else if (type === "new-registrations") {
    rows = await sql`
      SELECT inn, brand_name, holder, status, created_at, country_code
      FROM registrations
      WHERE created_at >= NOW() - INTERVAL '30 days'
        AND source_type != 'alert'
        AND (${country_code} = '' OR country_code = ${country_code})
      ORDER BY created_at DESC LIMIT 40
    `;
    const table = rows.map(r => `${r.brand_name || r.inn} (${r.inn}) | ${r.holder || "—"} | ${COUNTRIES[r.country_code as string] || r.country_code} | ${r.status} | ${fmt(r.created_at as string)}`).join("\n");
    userPrompt = `Write a blog post titled something like "New Pharmaceutical Registrations in ${countryName} — ${monthYear}".

Data: ${rows.length} new registrations added in the last 30 days${country_code ? ` in ${countryName}` : " across Africa"}.

Drug | Holder | Country | Status | Date Added
${table}

Analyse the trends: which therapeutic areas are growing, which companies are most active, what this signals for market access.`;
  } else if (type === "generic-opportunities") {
    rows = await sql`
      SELECT inn, brand_name, holder, expiry_date, country_code,
             COUNT(*) OVER (PARTITION BY inn) AS market_count
      FROM registrations
      WHERE status = 'expired'
        AND expiry_date >= NOW() - INTERVAL '3 years'
        AND source_type != 'alert'
        AND (${country_code} = '' OR country_code = ${country_code})
      ORDER BY expiry_date DESC LIMIT 40
    `;
    const table = rows.map(r => `${r.brand_name || r.inn} (${r.inn}) | ${r.holder || "—"} | ${COUNTRIES[r.country_code as string] || r.country_code} | ${fmt(r.expiry_date as string)}`).join("\n");
    userPrompt = `Write a blog post titled something like "Generic Drug Market Opportunities in ${countryName} — Expired Registrations Analysis ${now.getFullYear()}".

Data: ${rows.length} recently expired registrations${country_code ? ` in ${countryName}` : " across Africa"} representing potential generic entry points.

Drug | Original Holder | Country | Expired
${table}

Analyse which molecules represent the best generic opportunities — consider therapeutic importance, market size, and which registrations have no active alternatives.`;
  } else {
    // market-entry
    rows = await sql`
      SELECT DISTINCT w.inn, w.product_name, w.manufacturer, w.dosage_form,
             COUNT(r.id) AS african_registrations
      FROM who_prequalified w
      LEFT JOIN registrations r ON LOWER(r.inn) = LOWER(w.inn)
        AND r.status = 'active'
        AND source_type != 'alert'
        AND (${country_code} = '' OR r.country_code = ${country_code})
      GROUP BY w.inn, w.product_name, w.manufacturer, w.dosage_form
      HAVING COUNT(r.id) < 3
      ORDER BY COUNT(r.id) ASC LIMIT 30
    `;
    const table = rows.map(r => `${r.product_name} (${r.inn}) | ${r.manufacturer} | ${r.dosage_form} | ${r.african_registrations} markets`).join("\n");
    userPrompt = `Write a blog post titled something like "WHO Prequalified Drugs with Limited African Market Registration — ${countryName} Market Entry Intelligence ${now.getFullYear()}".

Data: ${rows.length} WHO prequalified medicines with fewer than 3 active registrations${country_code ? ` in ${countryName}` : " across tracked African markets"}.

Product | Manufacturer | Form | Active Registrations
${table}

Analyse the market access gaps — these represent opportunities for manufacturers to expand and unmet needs for patients.`;
  }

  if (rows.length === 0) {
    return Response.json({ skipped: true, reason: "No data found for this query" });
  }

  const llmRes = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${openrouterKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "google/gemini-2.5-flash",
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
    }),
  });

  if (!llmRes.ok) {
    const err = await llmRes.text();
    console.error("OpenRouter error:", err);
    return Response.json({ error: "LLM generation failed" }, { status: 502 });
  }

  const llmData = await llmRes.json() as { choices: { message: { content: string } }[] };
  let post: { title: string; description: string; content: string };
  try {
    post = JSON.parse(llmData.choices[0].message.content);
  } catch {
    return Response.json({ error: "LLM returned invalid JSON" }, { status: 502 });
  }

  const dateSlug = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const baseSlug = slugify(`${type}${country_code ? `-${country_code.toLowerCase()}` : ""}-${dateSlug}`);

  let slug = baseSlug;
  const [existing] = await sql`SELECT slug FROM blog_posts WHERE slug = ${slug}`;
  if (existing) {
    slug = `${baseSlug}-${Date.now()}`;
  }

  await sql`
    INSERT INTO blog_posts (slug, title, description, content, category, country_code)
    VALUES (${slug}, ${post.title}, ${post.description}, ${post.content}, ${type}, ${country_code || null})
  `;

  return Response.json({ ok: true, slug, title: post.title });
}
