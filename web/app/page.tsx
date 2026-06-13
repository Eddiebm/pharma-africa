"use client";

import { useState, useCallback, useEffect } from "react";
import SearchBar from "./components/SearchBar";
import ResultsTable from "./components/ResultsTable";

export interface Registration {
  id: string;
  inn: string;
  brand_name: string | null;
  country_code: string;
  country_name: string;
  registration_no: string | null;
  holder: string | null;
  status: string;
  expiry_date: string | null;
  dosage_forms: string[];
  last_verified: string;
}

export default function Home() {
  const [results, setResults] = useState<Registration[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState(false);
  const [statsDisplay, setStatsDisplay] = useState("161,000+");
  const [statsMarkets, setStatsMarkets] = useState(17);

  useEffect(() => {
    fetch("/api/stats").then(r => r.json()).then(d => {
      setStatsDisplay(d.display);
      setStatsMarkets(d.markets);
    }).catch(() => {});
  }, []);

  const handleSearch = useCallback(async (q: string, country: string, type: string = "") => {
    if (!q.trim()) return;
    setQuery(q);
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams({ q, ...(country && { country }), ...(type && { type }) });
      const res = await fetch(`/api/search?${params}`);
      const data = await res.json();
      setResults(data.results || []);
      setTotal(data.total || 0);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">AfricaRegulatory</h1>
            <p className="text-xs text-gray-500">African Pharmaceutical Regulatory Intelligence</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400 hidden sm:block">{statsDisplay} registrations · {statsMarkets} markets</span>
            <a href="/drugs" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">Drugs</a>
            <a href="/agri" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">Agri</a>
            <a href="/blog" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">Blog</a>
            <a href="/reports" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">Reports</a>
            <a href="/pricing" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">Pricing</a>
            <a href="/login" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">Sign in</a>
            <a href="/signup" className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">Sign up free</a>
          </div>
        </div>
      </header>

      <div className={`transition-all duration-300 ${searched ? "py-6 bg-white border-b border-gray-200" : "py-24"}`}>
        <div className="max-w-3xl mx-auto px-6">
          {!searched && (
            <div className="text-center mb-8">
              <h2 className="text-4xl font-bold text-gray-900 mb-3">
                Drug registration status across Africa
              </h2>
              <p className="text-lg text-gray-500">
                Search {statsDisplay} registrations across Nigeria, South Africa, Kenya, Ghana, Egypt, Senegal, Côte d'Ivoire, Tunisia, Morocco, Uganda, Rwanda, Malawi, Zimbabwe, Zambia and more.
              </p>
            </div>
          )}
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {searched && !loading && (
          <p className="mb-4 text-sm text-gray-500">
            {total > 0
              ? `${total} registration${total !== 1 ? "s" : ""} found for "${query}"`
              : `No registrations found for "${query}"`}
          </p>
        )}
        {loading && (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            Searching...
          </div>
        )}
        {!loading && results.length > 0 && <ResultsTable results={results} />}
        {!loading && searched && results.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-lg mb-2">No registrations found</p>
            <p className="text-sm">Try a different drug name, INN, or remove the country filter.</p>
          </div>
        )}
        {!searched && (
          <>
            <div className="text-center py-6 text-gray-400 text-sm">
              Try:{" "}
              {["amoxicillin", "metformin", "artemether", "tenofovir"].map((d, i) => (
                <span key={d}>
                  {i > 0 && " · "}
                  <button onClick={() => handleSearch(d, "")} className="text-blue-500 hover:underline">{d}</button>
                </span>
              ))}
            </div>

            {/* Stats bar */}
            <div className="grid grid-cols-3 gap-4 max-w-2xl mx-auto my-10 text-center">
              {[
                { value: statsDisplay, label: "Drug registrations" },
                { value: String(statsMarkets), label: "African markets" },
                { value: "Daily",   label: "Data updates" },
              ].map(s => (
                <div key={s.label} className="bg-white rounded-xl border border-gray-200 py-5 px-4">
                  <div className="text-2xl font-bold text-gray-900">{s.value}</div>
                  <div className="text-xs text-gray-500 mt-1">{s.label}</div>
                </div>
              ))}
            </div>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-4xl mx-auto my-10">
              {[
                {
                  icon: "🔍",
                  title: "Search by INN or brand name",
                  body: "Find any drug across all 16 markets in one query. Search by international non-proprietary name, brand name, or registration number.",
                },
                {
                  icon: "🌍",
                  title: "Filter by country, status & expiry",
                  body: "Narrow results to a single country or check registration status across the continent. Filter expired, active, or suspended products.",
                },
                {
                  icon: "📊",
                  title: "Export & API access",
                  body: "Download results as CSV or connect your systems via our API. Built for regulatory affairs teams, market access consultants, and pharma BD.",
                },
              ].map(f => (
                <div key={f.title} className="bg-white rounded-xl border border-gray-200 p-6">
                  <div className="text-2xl mb-3">{f.icon}</div>
                  <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{f.body}</p>
                </div>
              ))}
            </div>

            {/* Markets */}
            <div className="max-w-4xl mx-auto my-10">
              <h2 className="text-center text-lg font-semibold text-gray-900 mb-5">Markets covered</h2>
              <div className="flex flex-wrap justify-center gap-2">
                {[
                  { flag: "🇿🇦", name: "South Africa" },
                  { flag: "🇬🇭", name: "Ghana" },
                  { flag: "🇳🇬", name: "Nigeria" },
                  { flag: "🇨🇮", name: "Côte d'Ivoire" },
                  { flag: "🇸🇳", name: "Senegal" },
                  { flag: "🇲🇼", name: "Malawi" },
                  { flag: "🇪🇬", name: "Egypt" },
                  { flag: "🇹🇳", name: "Tunisia" },
                  { flag: "🇲🇦", name: "Morocco" },
                  { flag: "🇿🇲", name: "Zambia" },
                  { flag: "🇺🇬", name: "Uganda" },
                  { flag: "🇿🇼", name: "Zimbabwe" },
                  { flag: "🇲🇬", name: "Madagascar" },
                  { flag: "🇰🇪", name: "Kenya" },
                  { flag: "🇷🇼", name: "Rwanda" },
                  { flag: "🇹🇿", name: "Tanzania" },
                  { flag: "🇪🇹", name: "Ethiopia" },
                ].map(m => (
                  <span key={m.name} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 rounded-full text-sm text-gray-700">
                    {m.flag} {m.name}
                  </span>
                ))}
              </div>
            </div>

            {/* CTA banner */}
            <div className="max-w-2xl mx-auto my-10 bg-blue-600 rounded-2xl p-8 text-center text-white">
              <h2 className="text-xl font-bold mb-2">Ready to search the full register?</h2>
              <p className="text-blue-100 text-sm mb-5">Free plan includes 20 searches/month. No credit card required.</p>
              <a href="/signup" className="inline-block px-6 py-2.5 bg-white text-blue-600 text-sm font-semibold rounded-lg hover:bg-blue-50 transition-colors">
                Create free account →
              </a>
            </div>

            {/* Footer */}
            <footer className="max-w-6xl mx-auto py-10 px-6 border-t border-gray-200 mt-10 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-400">
              <span>© {new Date().getFullYear()} AfricaRegulatory. Data sourced from official national regulatory authorities.</span>
              <div className="flex gap-4">
                <a href="/markets" className="hover:text-gray-600">Markets</a>
                <a href="/pricing" className="hover:text-gray-600">Pricing</a>
                <a href="/blog" className="hover:text-gray-600">Blog</a>
                <a href="/privacy" className="hover:text-gray-600">Privacy</a>
                <a href="/terms" className="hover:text-gray-600">Terms</a>
              </div>
            </footer>
          </>
        )}
      </div>
    </main>
  );
}
