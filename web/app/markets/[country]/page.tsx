export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";

const MARKETS: Record<string, { name: string; code: string; regulator: string; regulatorUrl: string; slug: string }> = {
  nigeria:       { name: "Nigeria",        code: "NG", regulator: "NAFDAC",  regulatorUrl: "https://www.nafdac.gov.ng",         slug: "nigeria" },
  "south-africa":{ name: "South Africa",   code: "ZA", regulator: "SAHPRA",  regulatorUrl: "https://www.sahpra.org.za",         slug: "south-africa" },
  kenya:         { name: "Kenya",          code: "KE", regulator: "PPB",     regulatorUrl: "https://www.pharmacyboardkenya.org", slug: "kenya" },
  ghana:         { name: "Ghana",          code: "GH", regulator: "FDA Ghana",regulatorUrl: "https://fdaghana.gov.gh",           slug: "ghana" },
  egypt:         { name: "Egypt",          code: "EG", regulator: "EDA",     regulatorUrl: "https://www.eda.mohp.gov.eg",       slug: "egypt" },
  morocco:       { name: "Morocco",        code: "MA", regulator: "DMP",     regulatorUrl: "https://www.sante.gov.ma",          slug: "morocco" },
  tunisia:       { name: "Tunisia",        code: "TN", regulator: "DPM",     regulatorUrl: "https://www.santetunisie.rns.tn",   slug: "tunisia" },
  senegal:       { name: "Senegal",        code: "SN", regulator: "ARP",     regulatorUrl: "https://www.arp.sn",                slug: "senegal" },
  "cote-divoire":{ name: "Côte d'Ivoire",  code: "CI", regulator: "AIRP",    regulatorUrl: "https://www.airp.ci",               slug: "cote-divoire" },
  uganda:        { name: "Uganda",         code: "UG", regulator: "NDA",     regulatorUrl: "https://www.nda.or.ug",             slug: "uganda" },
  tanzania:      { name: "Tanzania",       code: "TZ", regulator: "TMDA",    regulatorUrl: "https://www.tmda.go.tz",            slug: "tanzania" },
  rwanda:        { name: "Rwanda",         code: "RW", regulator: "RDA",     regulatorUrl: "https://www.rda.gov.rw",            slug: "rwanda" },
  malawi:        { name: "Malawi",         code: "MW", regulator: "PMRA",    regulatorUrl: "https://www.pmra.org.mw",           slug: "malawi" },
  zambia:        { name: "Zambia",         code: "ZM", regulator: "ZAMRA",   regulatorUrl: "https://www.zamra.co.zm",           slug: "zambia" },
  zimbabwe:      { name: "Zimbabwe",       code: "ZW", regulator: "MCAZ",    regulatorUrl: "https://www.mcaz.co.zw",            slug: "zimbabwe" },
  ethiopia:      { name: "Ethiopia",       code: "ET", regulator: "EFDA",    regulatorUrl: "https://www.efda.gov.et",           slug: "ethiopia" },
};

type Stats = {
  total: number;
  active: number;
  expired: number;
  expiring_90d: number;
  last_scraped: string | null;
};

type TopDrug = {
  inn: string;
  brand_name: string | null;
  holder: string | null;
  status: string;
  expiry_date: string | null;
  registration_no: string | null;
  id: string;
};

async function getData(code: string): Promise<{ stats: Stats; topDrugs: TopDrug[] } | null> {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return null;
  const sql = neon(dbUrl);

  const [[stats], topDrugs] = await Promise.all([
    sql`
      SELECT
        COUNT(*)                                                              AS total,
        COUNT(*) FILTER (WHERE status = 'active')                            AS active,
        COUNT(*) FILTER (WHERE status = 'expired')                           AS expired,
        COUNT(*) FILTER (WHERE status = 'active'
          AND expiry_date BETWEEN NOW() AND NOW() + INTERVAL '90 days')      AS expiring_90d,
        rb.last_scraped
      FROM registrations r
      LEFT JOIN regulatory_bodies rb ON rb.country_code = ${code}
      WHERE r.country_code = ${code}
        AND r.source_type  != 'alert'
      GROUP BY rb.last_scraped
    `,
    sql`
      SELECT id, inn, brand_name, holder, status, expiry_date, registration_no
      FROM registrations
      WHERE country_code  = ${code}
        AND source_type  != 'alert'
        AND status        = 'active'
      ORDER BY last_verified DESC
      LIMIT 20
    `,
  ]);

  if (!stats) return null;
  return { stats: stats as unknown as Stats, topDrugs: topDrugs as unknown as TopDrug[] };
}

function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export async function generateMetadata({ params }: { params: Promise<{ country: string }> }): Promise<Metadata> {
  const { country } = await params;
  const market = MARKETS[country];
  if (!market) return {};
  return {
    title: `${market.name} Drug Registrations — AfricaRegulatory`,
    description: `Search ${market.name} pharmaceutical registrations regulated by ${market.regulator}. Active drugs, expiry dates, registration holders, and market access intelligence.`,
    alternates: { canonical: `https://africaregulatory.com/markets/${market.slug}` },
  };
}

export default async function CountryPage({ params }: { params: Promise<{ country: string }> }) {
  const { country } = await params;
  const market = MARKETS[country];
  if (!market) notFound();

  const result = await getData(market.code);
  if (!result) return <div className="p-8 text-red-600">Data unavailable</div>;

  const { stats, topDrugs } = result;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <Link href="/" className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors">AfricaRegulatory</Link>
            <p className="text-xs text-gray-500">African Pharmaceutical Regulatory Intelligence</p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/blog" className="text-sm text-gray-600 hover:text-gray-900">Blog</Link>
            <Link href="/pricing" className="text-sm text-gray-600 hover:text-gray-900">Pricing</Link>
            <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">Sign in</Link>
            <Link href="/signup" className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">Sign up free</Link>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-12">

        {/* Breadcrumb */}
        <div className="text-sm text-gray-500 mb-6">
          <Link href="/" className="hover:text-gray-900">Home</Link>
          <span className="mx-2">·</span>
          <Link href="/markets" className="hover:text-gray-900">Markets</Link>
          <span className="mx-2">·</span>
          <span className="text-gray-900">{market.name}</span>
        </div>

        {/* Hero */}
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {market.name} Pharmaceutical Drug Registrations
          </h1>
          <p className="text-gray-500 text-lg max-w-2xl">
            Searchable database of drugs registered by{" "}
            <a href={market.regulatorUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{market.regulator}</a>
            {" "}— the national pharmaceutical regulatory authority of {market.name}.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {[
            [Number(stats.total).toLocaleString(), "Total registrations"],
            [Number(stats.active).toLocaleString(), "Active registrations"],
            [Number(stats.expired).toLocaleString(), "Expired registrations"],
            [Number(stats.expiring_90d).toLocaleString(), "Expiring in 90 days"],
          ].map(([n, l]) => (
            <div key={l} className="bg-white border border-gray-200 rounded-xl p-5 text-center">
              <div className="text-2xl font-bold text-gray-900">{n}</div>
              <div className="text-xs text-gray-500 mt-1">{l}</div>
            </div>
          ))}
        </div>

        {/* Search CTA */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-6 mb-10 flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-gray-900">Search {market.name} registrations</p>
            <p className="text-sm text-gray-500 mt-0.5">Filter by drug name, INN, holder, or registration number</p>
          </div>
          <Link
            href={`/search?country=${market.code}`}
            className="shrink-0 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors"
          >
            Search {market.name} →
          </Link>
        </div>

        {/* Recently verified drugs */}
        <div className="mb-10">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Recently verified active registrations</h2>
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left">Drug</th>
                  <th className="px-4 py-3 text-left">INN</th>
                  <th className="px-4 py-3 text-left">Holder</th>
                  <th className="px-4 py-3 text-left">Reg No.</th>
                  <th className="px-4 py-3 text-left">Expires</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {topDrugs.map(drug => (
                  <tr key={drug.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <Link href={`/record/${drug.id}`} className="font-medium text-blue-600 hover:underline">
                        {drug.brand_name || drug.inn}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{drug.inn}</td>
                    <td className="px-4 py-3 text-gray-600">{drug.holder || "—"}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{drug.registration_no || "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{fmtDate(drug.expiry_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* About regulator */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-10">
          <h2 className="text-lg font-bold text-gray-900 mb-3">About {market.regulator}</h2>
          <p className="text-sm text-gray-600 leading-relaxed">
            {market.regulator} is the national pharmaceutical regulatory authority responsible for regulating
            the manufacture, importation, exportation, advertisement, distribution, sale, and use of food,
            drugs, cosmetics, medical devices, and chemicals in {market.name}. AfricaRegulatory continuously
            monitors {market.regulator} data to provide up-to-date registration status, expiry tracking,
            and market intelligence.
          </p>
          <a
            href={market.regulatorUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-3 text-sm text-blue-600 hover:underline"
          >
            Visit {market.regulator} official website →
          </a>
        </div>

        {/* Expiry alert CTA */}
        {Number(stats.expiring_90d) > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
            <p className="font-semibold text-amber-900">
              {Number(stats.expiring_90d).toLocaleString()} registration{Number(stats.expiring_90d) !== 1 ? "s" : ""} expiring in {market.name} within 90 days
            </p>
            <p className="text-sm text-amber-700 mt-1">
              Upgrade to Pro to receive automated expiry alerts 90 days before registrations lapse.
            </p>
            <Link
              href="/pricing"
              className="inline-block mt-3 px-4 py-2 bg-amber-600 text-white text-sm font-semibold rounded-lg hover:bg-amber-700 transition-colors"
            >
              Get expiry alerts →
            </Link>
          </div>
        )}

        {stats.last_scraped && (
          <p className="text-xs text-gray-400 mt-6 text-center">
            Data last verified: {fmtDate(stats.last_scraped)}
          </p>
        )}

      </div>
    </div>
  );
}
