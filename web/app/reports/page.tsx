export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Monthly Reports — AfricaRegulatory",
  description: "Monthly intelligence reports on African pharmaceutical regulation. Data-driven analysis of drug registrations, approvals, and market trends across 15 markets.",
};

type Report = {
  slug: string;
  title: string;
  description: string | null;
  pdf_path: string;
  period_start: string;
  period_end: string;
  published_at: string;
};

async function getReports(): Promise<Report[]> {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return [];
  const sql = neon(dbUrl);
  const rows = await sql`
    SELECT slug, title, description, pdf_path, period_start, period_end, published_at
    FROM monthly_reports ORDER BY period_start DESC LIMIT 24
  `;
  return rows as unknown as Report[];
}

function periodLabel(start: string, end: string) {
  return new Date(start).toLocaleDateString("en-GB", { month: "long", year: "numeric" });
}

export default async function ReportsPage() {
  const reports = await getReports();

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
            <Link href="/reports" className="text-sm font-medium text-blue-600">Reports</Link>
            <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">Sign in</Link>
            <Link href="/signup" className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">Sign up free</Link>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-10">
          <div className="inline-block bg-blue-50 text-blue-700 text-xs font-semibold px-3 py-1 rounded-full mb-4">Published monthly</div>
          <h1 className="text-3xl font-bold text-gray-900">State of African Pharmaceutical Regulation</h1>
          <p className="text-gray-500 mt-3 leading-relaxed max-w-2xl">
            Comprehensive monthly intelligence reports covering new drug approvals, registration expirations, market trends, and WHO prequalification updates across 15 African markets.
          </p>
        </div>

        {reports.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
            <p className="text-gray-400 text-lg mb-2">First report coming soon</p>
            <p className="text-gray-400 text-sm">Published on the 1st of each month.</p>
          </div>
        ) : (
          <div className="grid gap-6">
            {reports.map((report, i) => (
              <div key={report.slug} className={`bg-white border rounded-xl overflow-hidden ${i === 0 ? "border-blue-200 shadow-sm" : "border-gray-200"}`}>
                {i === 0 && (
                  <div className="bg-blue-600 px-6 py-2">
                    <span className="text-white text-xs font-semibold tracking-wide">LATEST REPORT</span>
                  </div>
                )}
                <div className="p-6 flex items-start justify-between gap-6">
                  <div className="flex-1">
                    <div className="text-xs text-gray-400 mb-2 font-medium">
                      {periodLabel(report.period_start, report.period_end)}
                    </div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-2">{report.title}</h2>
                    {report.description && (
                      <p className="text-sm text-gray-500 leading-relaxed">{report.description}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-3">
                      Published {new Date(report.published_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
                    </p>
                  </div>
                  <div className="shrink-0 flex flex-col gap-2">
                    <a
                      href={report.pdf_path}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                      </svg>
                      Download PDF
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-16 bg-blue-50 border border-blue-100 rounded-xl p-8 text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Get reports delivered to your inbox</h2>
          <p className="text-gray-500 mb-6 text-sm">AfriReg Pro members receive each monthly report automatically, plus weekly expiry alerts for their tracked markets.</p>
          <Link href="/signup" className="inline-block px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors">
            Start free — no credit card required
          </Link>
        </div>
      </div>
    </div>
  );
}
