export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Drug Registrations Across Africa — AfricaRegulatory",
  description: "Browse registration status for 1,400+ drug molecules across 17 African markets. See which countries have approved each active ingredient, registration holders, and expiry dates.",
  alternates: { canonical: "https://africaregulatory.com/drugs" },
};

type DrugRow = {
  inn: string;
  slug: string;
  markets: number;
  records: number;
};

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

async function getDrugs(): Promise<DrugRow[]> {
  const sql = neon(process.env.DATABASE_URL!);
  const rows = await sql`
    SELECT
      lower(trim(inn))                                                    AS inn,
      lower(regexp_replace(trim(inn), '[^a-zA-Z0-9]+', '-', 'g'))        AS slug,
      COUNT(DISTINCT country_code)::int                                   AS markets,
      COUNT(*)::int                                                       AS records
    FROM registrations
    WHERE inn IS NOT NULL
      AND length(trim(inn)) > 2
      AND lower(trim(inn)) NOT IN ('none', 'n/a', '-', '—', 'various', 'not applicable')
    GROUP BY lower(trim(inn)), slug
    HAVING COUNT(DISTINCT country_code) >= 3
    ORDER BY markets DESC, records DESC
    LIMIT 2000
  `;
  return rows as DrugRow[];
}

function titleCase(s: string) {
  return s.replace(/\b\w/g, c => c.toUpperCase());
}

export default async function DrugsIndexPage() {
  const drugs = await getDrugs();

  const byLetter: Record<string, DrugRow[]> = {};
  for (const d of drugs) {
    const letter = d.inn[0].toUpperCase();
    if (!byLetter[letter]) byLetter[letter] = [];
    byLetter[letter].push(d);
  }

  const presentLetters = LETTERS.filter(l => byLetter[l]?.length);

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <Link href="/" className="text-xl font-bold text-gray-900 hover:text-blue-600">AfricaRegulatory</Link>
            <p className="text-xs text-gray-500">African Pharmaceutical Regulatory Intelligence</p>
          </div>
          <div className="flex gap-3 items-center">
            <Link href="/markets" className="text-sm text-gray-600 hover:text-gray-900">Markets</Link>
            <Link href="/pricing" className="text-sm text-gray-600 hover:text-gray-900">Pricing</Link>
            <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">Sign in</Link>
            <Link href="/signup" className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">Sign up free</Link>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-10">
        <nav className="text-sm text-gray-500 mb-6">
          <Link href="/" className="hover:text-gray-700">Home</Link>
          <span className="mx-2">›</span>
          <span className="text-gray-900">Drug Index</span>
        </nav>

        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Drug Registrations in Africa</h1>
          <p className="text-gray-500 text-lg max-w-2xl">
            {drugs.length.toLocaleString()} active pharmaceutical ingredients — browse registration status across 17 African markets, sourced daily from official national drug authorities.
          </p>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-3 gap-4 mb-10">
          {[
            { value: `${drugs.filter(d => d.markets >= 10).length}`, label: "in 10+ markets" },
            { value: `${drugs.filter(d => d.markets >= 5).length}`, label: "in 5+ markets" },
            { value: drugs.length.toLocaleString(), label: "total molecules" },
          ].map(s => (
            <div key={s.label} className="bg-white border border-gray-200 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-gray-900">{s.value}</div>
              <div className="text-sm text-gray-500">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Alphabet jump nav */}
        <div className="flex flex-wrap gap-1.5 mb-8">
          {LETTERS.map(l => (
            presentLetters.includes(l) ? (
              <a key={l} href={`#${l}`} className="w-8 h-8 flex items-center justify-center rounded-lg bg-white border border-gray-200 text-sm font-medium text-gray-700 hover:border-blue-400 hover:text-blue-600 transition-colors">{l}</a>
            ) : (
              <span key={l} className="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-gray-300">{l}</span>
            )
          ))}
        </div>

        {/* Drug list by letter */}
        <div className="space-y-10">
          {presentLetters.map(letter => (
            <section key={letter} id={letter}>
              <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b border-gray-200">{letter}</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {byLetter[letter].map(d => (
                  <Link
                    key={d.slug}
                    href={`/drugs/${d.slug}`}
                    className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-4 py-2.5 hover:border-blue-300 hover:shadow-sm transition-all group"
                  >
                    <span className="text-sm font-medium text-gray-800 group-hover:text-blue-700 capitalize">{titleCase(d.inn)}</span>
                    <span className="text-xs text-gray-400 ml-2 shrink-0">{d.markets} {d.markets === 1 ? "market" : "markets"}</span>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>

        {/* SEO footer text */}
        <section className="mt-16 pt-8 border-t border-gray-200">
          <h2 className="text-base font-semibold text-gray-900 mb-3">About this index</h2>
          <p className="text-sm text-gray-500 leading-relaxed max-w-3xl">
            AfricaRegulatory aggregates drug registration data daily from 17 official national drug regulatory authorities across Africa —
            including NAFDAC (Nigeria), PPB (Kenya), FDA Ghana, SAHPRA (South Africa), EDA (Egypt), TMDA (Tanzania), and 11 more.
            Each entry represents a distinct active pharmaceutical ingredient (INN) with at least one active registration on record.
            Use this index to assess pan-African market coverage for any molecule, identify registration gaps,
            and track expiry risk across markets.{" "}
            <Link href="/signup" className="text-blue-600 hover:underline">Sign up free</Link> to search, filter, and export registration data.
          </p>
        </section>
      </div>
    </main>
  );
}
