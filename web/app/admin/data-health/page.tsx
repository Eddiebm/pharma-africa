export const runtime = "edge";
export const dynamic = "force-dynamic";

import { neon } from "@neondatabase/serverless";
import { notFound } from "next/navigation";

type CountryHealth = {
  country_code: string;
  name: string;
  last_scraped: string | null;
  total: number;
  active: number;
  verified_30d: number;
  verified_90d: number;
  stale: number;
  expiring_90d: number;
};

type Summary = {
  total: number;
  verified_30d: number;
  verified_90d: number;
  stale: number;
  last_run: string | null;
};

async function getHealthData(): Promise<{ rows: CountryHealth[]; summary: Summary } | null> {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return null;
  const sql = neon(dbUrl);

  const [rows, [summary]] = await Promise.all([
    sql`
      SELECT
        r.country_code,
        COALESCE(rb.name, r.country_code)                                                    AS name,
        rb.last_scraped,
        COUNT(r.id)                                                                          AS total,
        COUNT(r.id) FILTER (WHERE r.status = 'active')                                       AS active,
        COUNT(r.id) FILTER (WHERE r.last_verified >= NOW() - INTERVAL '30 days')             AS verified_30d,
        COUNT(r.id) FILTER (WHERE r.last_verified >= NOW() - INTERVAL '90 days'
                             AND   r.last_verified <  NOW() - INTERVAL '30 days')            AS verified_90d,
        COUNT(r.id) FILTER (WHERE r.last_verified <  NOW() - INTERVAL '90 days')             AS stale,
        COUNT(r.id) FILTER (WHERE r.status = 'active'
                             AND   r.expiry_date BETWEEN NOW() AND NOW() + INTERVAL '90 days') AS expiring_90d
      FROM registrations r
      LEFT JOIN regulatory_bodies rb ON rb.country_code = r.country_code
      WHERE r.source_type != 'alert'
      GROUP BY r.country_code, rb.name, rb.last_scraped
      ORDER BY stale DESC, total DESC
    `,
    sql`
      SELECT
        COUNT(*)                                                                             AS total,
        COUNT(*) FILTER (WHERE last_verified >= NOW() - INTERVAL '30 days')                 AS verified_30d,
        COUNT(*) FILTER (WHERE last_verified >= NOW() - INTERVAL '90 days')                 AS verified_90d,
        COUNT(*) FILTER (WHERE last_verified <  NOW() - INTERVAL '90 days')                 AS stale,
        MAX(last_verified)                                                                   AS last_run
      FROM registrations
      WHERE source_type != 'alert'
    `,
  ]);

  return {
    rows: rows as unknown as CountryHealth[],
    summary: summary as unknown as Summary,
  };
}

function pct(n: number, total: number) {
  if (!total) return 0;
  return Math.round((n / total) * 100);
}

function fmtDate(d: string | null) {
  if (!d) return "never";
  const date = new Date(d);
  const diffDays = Math.floor((Date.now() - date.getTime()) / 86400000);
  if (diffDays === 0) return "today";
  if (diffDays === 1) return "yesterday";
  return `${diffDays}d ago`;
}

function StatusBadge({ stale, total }: { stale: number; total: number }) {
  const pctStale = pct(stale, total);
  if (pctStale === 0) return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">Fresh</span>;
  if (pctStale < 20)  return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">Aging</span>;
  return                     <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">Stale</span>;
}

export default async function DataHealthPage({
  searchParams,
}: {
  searchParams: Promise<{ key?: string }>;
}) {
  const { key } = await searchParams;
  if (!key || key !== process.env.CRON_SECRET) notFound();

  const data = await getHealthData();
  if (!data) return <div className="p-8 text-red-600">Database unavailable</div>;

  const { rows, summary } = data;
  const overallPct = pct(Number(summary.verified_30d), Number(summary.total));

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8 font-mono">
      <div className="max-w-6xl mx-auto">

        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">Data Health Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">
            Last verification: {fmtDate(summary.last_run)} · {Number(summary.total).toLocaleString()} total records
          </p>
        </div>

        {/* Top-level summary cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold text-white">{Number(summary.total).toLocaleString()}</div>
            <div className="text-xs text-gray-400 mt-1">Total records</div>
          </div>
          <div className="bg-gray-900 border border-green-900 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-400">{Number(summary.verified_30d).toLocaleString()}</div>
            <div className="text-xs text-gray-400 mt-1">Verified &lt;30 days ({overallPct}%)</div>
          </div>
          <div className="bg-gray-900 border border-yellow-900 rounded-lg p-4">
            <div className="text-2xl font-bold text-yellow-400">
              {(Number(summary.verified_90d) - Number(summary.verified_30d)).toLocaleString()}
            </div>
            <div className="text-xs text-gray-400 mt-1">Verified 30–90 days</div>
          </div>
          <div className="bg-gray-900 border border-red-900 rounded-lg p-4">
            <div className="text-2xl font-bold text-red-400">{Number(summary.stale).toLocaleString()}</div>
            <div className="text-xs text-gray-400 mt-1">Stale &gt;90 days</div>
          </div>
        </div>

        {/* Per-country table */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Country</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3 text-right">Active</th>
                <th className="px-4 py-3 text-right text-green-400">&lt;30d</th>
                <th className="px-4 py-3 text-right text-yellow-400">30–90d</th>
                <th className="px-4 py-3 text-right text-red-400">&gt;90d stale</th>
                <th className="px-4 py-3 text-right">Expiring 90d</th>
                <th className="px-4 py-3 text-right">Last scraped</th>
                <th className="px-4 py-3 text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {rows.map(row => (
                <tr key={row.country_code} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="text-white font-medium">{row.name}</span>
                    <span className="text-gray-500 text-xs ml-2">{row.country_code}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">{Number(row.total).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-gray-300">{Number(row.active).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-green-400">{Number(row.verified_30d).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-yellow-400">{Number(row.verified_90d).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={Number(row.stale) > 0 ? "text-red-400 font-medium" : "text-gray-500"}>
                      {Number(row.stale).toLocaleString()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-orange-400">{Number(row.expiring_90d).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-gray-400 text-xs">{fmtDate(row.last_scraped)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge stale={Number(row.stale)} total={Number(row.total)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-gray-600 mt-6">
          Stale = last_verified &gt; 90 days ago. Refresh by running the scraper for that country.
        </p>
      </div>
    </div>
  );
}
