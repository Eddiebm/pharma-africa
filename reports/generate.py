#!/usr/bin/env python3
"""
AfricaRegulatory Monthly Report Generator
Usage: python3 generate.py [--month YYYY-MM]
"""
import os, sys, json, argparse, httpx, psycopg2, psycopg2.extras
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/opt/pharma-scraper/.env")

DATABASE_URL   = os.environ["DATABASE_URL"]
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
RESEND_KEY     = os.environ.get("RESEND_API_KEY", "")
REPORTS_DIR    = Path("/opt/afireg-reports")

COUNTRIES = {
    "ZA": "South Africa", "NG": "Nigeria", "KE": "Kenya", "GH": "Ghana", "RW": "Rwanda",
    "TZ": "Tanzania", "UG": "Uganda", "ET": "Ethiopia", "ZM": "Zambia", "ZW": "Zimbabwe",
    "MA": "Morocco", "MW": "Malawi", "EG": "Egypt", "SN": "Senegal", "CI": "Côte d'Ivoire",
    "TN": "Tunisia", "MG": "Madagascar", "MZ": "Mozambique", "AO": "Angola", "WW": "WHO",
}
PRIORITY = ["NG", "ZA", "KE", "GH", "EG", "MA", "TN", "CI", "SN", "UG", "TZ", "MW", "ZM", "ZW", "RW"]


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def query(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def gather_data(conn, period_start, period_end):
    data = {}

    data["totals"] = query(conn, """
        SELECT country_code, status, COUNT(*) as n
        FROM registrations WHERE source_type != 'alert'
        GROUP BY country_code, status
    """)

    data["new_this_period"] = query(conn, """
        SELECT country_code, COUNT(*) as n
        FROM registrations
        WHERE source_type != 'alert' AND created_at >= %s AND created_at < %s
        GROUP BY country_code ORDER BY n DESC
    """, (period_start, period_end))

    data["expiring_90"] = query(conn, """
        SELECT country_code, COUNT(*) as n
        FROM registrations
        WHERE status = 'active' AND source_type != 'alert'
          AND expiry_date BETWEEN NOW() AND NOW() + INTERVAL '90 days'
        GROUP BY country_code ORDER BY n DESC
    """)

    data["top_holders"] = query(conn, """
        SELECT holder, COUNT(*) as n FROM registrations
        WHERE status = 'active' AND source_type != 'alert' AND holder IS NOT NULL
        GROUP BY holder ORDER BY n DESC LIMIT 20
    """)

    data["who_pq"] = query(conn, """
        SELECT w.inn, w.product_name, w.manufacturer, w.dosage_form,
               COUNT(r.id) as african_regs
        FROM who_prequalified w
        LEFT JOIN registrations r ON LOWER(r.inn) = LOWER(w.inn) AND r.status = 'active'
        GROUP BY w.inn, w.product_name, w.manufacturer, w.dosage_form
        ORDER BY african_regs DESC LIMIT 15
    """)

    return data


def write_narrative(data, period_label):
    if not OPENROUTER_KEY:
        return {
            "executive_summary": "Narrative generation requires OPENROUTER_API_KEY to be configured.",
            "key_trends": "Please set OPENROUTER_API_KEY in /opt/pharma-scraper/.env.",
            "outlook": ""
        }

    total_active   = sum(int(r["n"]) for r in data["totals"] if r["status"] == "active")
    total_new      = sum(int(r["n"]) for r in data["new_this_period"])
    total_expiring = sum(int(r["n"]) for r in data["expiring_90"])
    top_markets    = [
        f"{COUNTRIES.get(r['country_code'], r['country_code'])} ({r['n']} new)"
        for r in data["new_this_period"][:5]
    ]

    prompt = f"""Write three sections for a professional pharmaceutical regulatory intelligence report for {period_label}.

Statistics:
- Total active registrations across Africa: {total_active:,}
- New registrations this period: {total_new:,}
- Active registrations expiring within 90 days: {total_expiring:,}
- Most active markets this period: {', '.join(top_markets)}

Return JSON with exactly these keys:
{{
  "executive_summary": "3 paragraphs, data-driven, authoritative tone, cite the specific numbers",
  "key_trends": "2 paragraphs on notable regulatory trends across African markets",
  "outlook": "1 paragraph on what regulatory teams should watch in the coming months"
}}"""

    r = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
        json={
            "model": "google/gemini-2.5-flash",
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def build_html(data, narrative, period_label):
    total_active   = sum(int(r["n"]) for r in data["totals"] if r["status"] == "active")
    total_new      = sum(int(r["n"]) for r in data["new_this_period"])
    total_expiring = sum(int(r["n"]) for r in data["expiring_90"])

    country_active  = {r["country_code"]: int(r["n"]) for r in data["totals"] if r["status"] == "active"}
    country_expired = {r["country_code"]: int(r["n"]) for r in data["totals"] if r["status"] == "expired"}
    country_new     = {r["country_code"]: int(r["n"]) for r in data["new_this_period"]}
    country_exp90   = {r["country_code"]: int(r["n"]) for r in data["expiring_90"]}

    country_rows = ""
    for cc in PRIORITY:
        name    = COUNTRIES.get(cc, cc)
        active  = country_active.get(cc, 0)
        expired = country_expired.get(cc, 0)
        new_n   = country_new.get(cc, 0)
        exp90   = country_exp90.get(cc, 0)
        country_rows += f"<tr><td>{name}</td><td>{active:,}</td><td>{new_n:,}</td><td>{exp90:,}</td><td>{expired:,}</td></tr>\n"

    holder_rows = ""
    for r in data["top_holders"][:15]:
        holder_rows += f"<tr><td>{r['holder'] or '—'}</td><td>{int(r['n']):,}</td></tr>\n"

    who_rows = ""
    for r in data["who_pq"][:12]:
        who_rows += f"<tr><td>{r['product_name']}</td><td>{r['inn']}</td><td>{r['manufacturer']}</td><td>{r['dosage_form'] or '—'}</td><td>{int(r['african_regs'])}</td></tr>\n"

    def paras(text):
        return "".join(f"<p>{p.strip()}</p>" for p in (text or "").split("\n\n") if p.strip())

    published = datetime.now().strftime("%-d %B %Y")

    css = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    @page { size: A4; margin: 18mm 20mm 22mm 20mm; }
    @page { @bottom-center { content: "AfricaRegulatory.com  ·  Confidential"; font-size: 9pt; color: #94a3b8; }
            @bottom-right  { content: "Page " counter(page); font-size: 9pt; color: #94a3b8; } }
    body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #1e293b; line-height: 1.6; }
    .cover { page-break-after: always; background: #0f2744; color: white;
             min-height: 270mm; display: flex; flex-direction: column;
             justify-content: space-between; padding: 40mm 30mm;
             margin: -18mm -20mm -22mm -20mm; }
    .cover-badge { background: rgba(59,130,246,0.3); border: 1px solid rgba(59,130,246,0.5);
                   display: inline-block; padding: 4px 14px; border-radius: 20px;
                   font-size: 9pt; color: #93c5fd; letter-spacing: 0.08em; margin-bottom: 24px; }
    .cover-title { font-size: 32pt; font-weight: 700; line-height: 1.15; margin-bottom: 16px; }
    .cover-sub   { font-size: 14pt; color: #93c5fd; margin-bottom: 40px; }
    .cover-stats { display: flex; gap: 48px; margin-bottom: 40px; }
    .cover-stat-n { font-size: 26pt; font-weight: 700; color: white; }
    .cover-stat-l { font-size: 9pt; color: #93c5fd; margin-top: 4px; }
    .cover-footer { border-top: 1px solid rgba(255,255,255,0.15); padding-top: 20px;
                    display: flex; justify-content: space-between; align-items: center; }
    .cover-brand { font-size: 13pt; font-weight: 700; color: white; letter-spacing: 0.02em; }
    .cover-date  { font-size: 10pt; color: #93c5fd; }
    .toc { page-break-after: always; }
    h1 { font-size: 18pt; font-weight: 700; color: #0f2744; margin-bottom: 12px;
         padding-bottom: 8px; border-bottom: 2px solid #3b82f6; }
    h2 { font-size: 13pt; font-weight: 700; color: #0f2744; margin: 20px 0 10px; }
    p  { margin-bottom: 10px; color: #374151; }
    .section { page-break-before: always; padding-top: 4px; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 9pt; }
    thead { background: #0f2744; color: white; }
    th { padding: 7px 10px; text-align: left; font-weight: 600; white-space: nowrap; }
    td { padding: 6px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
    tr:nth-child(even) td { background: #f8fafc; }
    .metric-grid { display: flex; gap: 16px; margin: 16px 0 24px; }
    .metric      { flex: 1; background: #f0f9ff; border: 1px solid #bae6fd;
                   border-radius: 8px; padding: 14px 16px; }
    .metric-n    { font-size: 20pt; font-weight: 700; color: #0369a1; }
    .metric-l    { font-size: 8pt; color: #0284c7; margin-top: 3px;
                   text-transform: uppercase; letter-spacing: 0.05em; }
    .toc-item    { display: flex; justify-content: space-between; padding: 6px 0;
                   border-bottom: 1px dotted #e2e8f0; font-size: 10pt; }
    .toc-num     { color: #64748b; }
    .disclaimer  { margin-top: 20px; font-size: 8pt; color: #94a3b8;
                   border-top: 1px solid #e2e8f0; padding-top: 12px; }
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{css}</style></head>
<body>

<div class="cover">
  <div>
    <div class="cover-badge">MONTHLY INTELLIGENCE REPORT</div>
    <div class="cover-title">State of African<br>Pharmaceutical<br>Regulation</div>
    <div class="cover-sub">{period_label}</div>
    <div class="cover-stats">
      <div><div class="cover-stat-n">{total_active:,}</div><div class="cover-stat-l">Active Registrations</div></div>
      <div><div class="cover-stat-n">{total_new:,}</div><div class="cover-stat-l">New This Period</div></div>
      <div><div class="cover-stat-n">{total_expiring:,}</div><div class="cover-stat-l">Expiring in 90 Days</div></div>
      <div><div class="cover-stat-n">15</div><div class="cover-stat-l">Markets Tracked</div></div>
    </div>
  </div>
  <div class="cover-footer">
    <div class="cover-brand">AFRICAREGULATORY.COM</div>
    <div class="cover-date">Published {published}</div>
  </div>
</div>

<div class="toc">
  <h1>Table of Contents</h1>
  <div style="margin-top:20px;">
    <div class="toc-item"><span>1. Executive Summary</span><span class="toc-num">3</span></div>
    <div class="toc-item"><span>2. Key Trends</span><span class="toc-num">4</span></div>
    <div class="toc-item"><span>3. Market-by-Market Overview</span><span class="toc-num">5</span></div>
    <div class="toc-item"><span>4. Top Registration Holders</span><span class="toc-num">6</span></div>
    <div class="toc-item"><span>5. WHO Prequalification Status</span><span class="toc-num">7</span></div>
    <div class="toc-item"><span>6. Outlook</span><span class="toc-num">8</span></div>
    <div class="toc-item"><span>Appendix: Methodology &amp; Data Sources</span><span class="toc-num">9</span></div>
  </div>
</div>

<div class="section">
  <h1>1. Executive Summary</h1>
  <div class="metric-grid">
    <div class="metric"><div class="metric-n">{total_active:,}</div><div class="metric-l">Active Registrations</div></div>
    <div class="metric"><div class="metric-n">{total_new:,}</div><div class="metric-l">New This Period</div></div>
    <div class="metric"><div class="metric-n">{total_expiring:,}</div><div class="metric-l">Expiring ≤ 90 Days</div></div>
  </div>
  {paras(narrative.get("executive_summary", ""))}
</div>

<div class="section">
  <h1>2. Key Trends</h1>
  {paras(narrative.get("key_trends", ""))}
</div>

<div class="section">
  <h1>3. Market-by-Market Overview</h1>
  <table>
    <thead><tr><th>Market</th><th>Active</th><th>New This Period</th><th>Expiring ≤ 90d</th><th>Expired</th></tr></thead>
    <tbody>{country_rows}</tbody>
  </table>
</div>

<div class="section">
  <h1>4. Top Registration Holders</h1>
  <p>Companies with the most active drug registrations across all tracked African markets.</p>
  <table>
    <thead><tr><th>Company / Holder</th><th>Active Registrations</th></tr></thead>
    <tbody>{holder_rows}</tbody>
  </table>
</div>

<div class="section">
  <h1>5. WHO Prequalification Status</h1>
  <p>WHO prequalified medicines and their current registration footprint across African markets.</p>
  <table>
    <thead><tr><th>Product</th><th>INN</th><th>Manufacturer</th><th>Form</th><th>African Regs</th></tr></thead>
    <tbody>{who_rows}</tbody>
  </table>
</div>

<div class="section">
  <h1>6. Outlook</h1>
  {paras(narrative.get("outlook", ""))}
  <div class="disclaimer">
    This report is generated automatically from AfricaRegulatory's database of 95,000+ pharmaceutical
    registrations across 15 African markets. Data is sourced directly from national regulatory authority
    websites. Registration counts reflect the state of the database at time of generation.
    AfricaRegulatory.com · eddie@bannermanmenson.com
  </div>
</div>

<div class="section">
  <h1>Appendix: Methodology &amp; Data Sources</h1>
  <h2>Data Collection</h2>
  <p>AfricaRegulatory operates automated scrapers that visit each national regulatory authority's public
  database daily. Data is normalised to a common schema and stored in a centralised Neon PostgreSQL database.</p>
  <h2>Coverage</h2>
  <table>
    <thead><tr><th>Country</th><th>Regulatory Body</th><th>Update Frequency</th></tr></thead>
    <tbody>
      <tr><td>Nigeria</td><td>NAFDAC</td><td>Daily</td></tr>
      <tr><td>South Africa</td><td>SAHPRA</td><td>Daily</td></tr>
      <tr><td>Kenya</td><td>PPB</td><td>Daily</td></tr>
      <tr><td>Ghana</td><td>FDA</td><td>Daily</td></tr>
      <tr><td>Egypt</td><td>EDA</td><td>Daily</td></tr>
      <tr><td>Morocco</td><td>DMP</td><td>Daily</td></tr>
      <tr><td>Tunisia</td><td>DPM</td><td>Daily</td></tr>
      <tr><td>Côte d'Ivoire</td><td>AIRP</td><td>Daily</td></tr>
      <tr><td>Senegal</td><td>ARP</td><td>Daily</td></tr>
      <tr><td>Uganda</td><td>NDA</td><td>Daily</td></tr>
      <tr><td>Tanzania</td><td>TMDA</td><td>Daily</td></tr>
      <tr><td>Malawi</td><td>PMRA</td><td>Daily</td></tr>
      <tr><td>Zambia</td><td>ZAMRA</td><td>Daily</td></tr>
      <tr><td>Zimbabwe</td><td>MCAZ</td><td>Daily</td></tr>
      <tr><td>Rwanda</td><td>RDA</td><td>Daily</td></tr>
    </tbody>
  </table>
</div>

</body>
</html>"""


def send_to_press(conn, pdf_url, title, period_label):
    if not RESEND_KEY:
        print("RESEND_API_KEY not set — skipping press distribution")
        return 0

    contacts = query(conn, "SELECT email, name FROM press_contacts WHERE active = true")
    if not contacts:
        print("No active press contacts in database")
        return 0

    sent = 0
    for contact in contacts:
        name = contact["name"] or "there"
        body = f"""<p>Hi {name},</p>
<p>The <strong>{title}</strong> is now available from AfricaRegulatory.</p>
<p><a href="{pdf_url}" style="background:#1d4ed8;color:white;padding:10px 20px;border-radius:6px;
   text-decoration:none;display:inline-block;margin:12px 0">Download Report (PDF)</a></p>
<p>This month's report covers new drug approvals, expiry alerts, top registration holders, and
WHO prequalification status across 15 African markets — sourced from official regulatory authority
databases updated daily.</p>
<p>—<br>AfricaRegulatory Intelligence<br>
<a href="https://africaregulatory.com">africaregulatory.com</a></p>
<p style="font-size:11px;color:#94a3b8;margin-top:20px">
You are receiving this because you are on the AfricaRegulatory press distribution list.
Reply to unsubscribe.</p>"""

        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
            json={
                "from": "AfricaRegulatory <reports@africaregulatory.com>",
                "to": contact["email"],
                "subject": f"{title} — AfricaRegulatory",
                "html": body
            },
            timeout=30
        )
        if r.status_code in (200, 201):
            sent += 1
        else:
            print(f"Failed to send to {contact['email']}: {r.text}")
    return sent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="YYYY-MM  (defaults to previous month)")
    args = parser.parse_args()

    if args.month:
        period_start = datetime.strptime(args.month, "%Y-%m").date().replace(day=1)
    else:
        today = date.today()
        period_start = (today.replace(day=1) - relativedelta(months=1))

    period_end   = period_start + relativedelta(months=1)
    slug         = period_start.strftime("%Y-%m")
    period_label = period_start.strftime("%B %Y")
    title        = f"State of African Pharmaceutical Regulation — {period_label}"
    pdf_filename = f"africaregulatory-report-{slug}.pdf"
    pdf_path     = REPORTS_DIR / pdf_filename
    pdf_url      = f"https://africaregulatory.com/reports/{pdf_filename}"

    print(f"Generating: {title}")

    conn = get_conn()

    existing = query(conn, "SELECT id FROM reports WHERE slug = %s", (slug,))
    if existing:
        print(f"Report for {slug} already exists — delete from DB to regenerate")
        conn.close()
        sys.exit(0)

    print("Querying database...")
    data = gather_data(conn, period_start, period_end)

    print("Writing narrative...")
    narrative = write_narrative(data, period_label)

    print("Building HTML...")
    html = build_html(data, narrative, period_label)

    print(f"Rendering PDF → {pdf_path}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(path=str(pdf_path), format="A4", print_background=True)
        browser.close()
    print(f"PDF saved ({pdf_path.stat().st_size // 1024}KB)")

    total_new      = sum(int(r["n"]) for r in data["new_this_period"])
    total_expiring = sum(int(r["n"]) for r in data["expiring_90"])
    description = (
        f"Analysis of {total_new:,} new registrations and {total_expiring:,} upcoming "
        f"expirations across 15 African markets."
    )

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO reports (slug, title, description, pdf_path, period_start, period_end) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (slug, title, description, f"/reports/{pdf_filename}", period_start, period_end)
        )
    conn.commit()
    print(f"Saved to DB")

    print("Distributing to press...")
    sent = send_to_press(conn, pdf_url, title, period_label)
    if sent:
        with conn.cursor() as cur:
            cur.execute("UPDATE reports SET sent_to_press = true WHERE slug = %s", (slug,))
        conn.commit()
        print(f"Sent to {sent} press contacts")

    conn.close()
    print(f"Done → {pdf_url}")


if __name__ == "__main__":
    main()
