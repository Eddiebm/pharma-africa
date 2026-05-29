"use client";

import { useState, useCallback } from "react";
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

  const handleSearch = useCallback(async (q: string, country: string) => {
    if (!q.trim()) return;
    setQuery(q);
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams({ q, ...(country && { country }) });
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
            <h1 className="text-xl font-bold text-gray-900">AfriReg</h1>
            <p className="text-xs text-gray-500">African Pharmaceutical Regulatory Intelligence</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400 hidden sm:block">90,000+ registrations · 15 African markets</span>
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
                Search 90,000+ registrations across Nigeria, South Africa, Kenya, Ghana, Senegal, Côte d'Ivoire, Tunisia, Morocco, Madagascar, Uganda, Rwanda, Malawi, Zimbabwe, Zambia and more.
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
          <div className="text-center py-8 text-gray-400 text-sm">
            Try:{" "}
            {["amoxicillin", "metformin", "artemether", "tenofovir"].map((d, i) => (
              <span key={d}>
                {i > 0 && " · "}
                <button onClick={() => handleSearch(d, "")} className="text-blue-500 hover:underline">{d}</button>
              </span>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
