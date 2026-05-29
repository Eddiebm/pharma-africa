"use client";

import { useState, useCallback, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";

const COUNTRIES = [
  { code: "", name: "All markets" },
  { code: "ZA", name: "South Africa" }, { code: "NG", name: "Nigeria" },
  { code: "KE", name: "Kenya" }, { code: "GH", name: "Ghana" },
  { code: "RW", name: "Rwanda" }, { code: "TZ", name: "Tanzania" },
  { code: "UG", name: "Uganda" }, { code: "ET", name: "Ethiopia" },
  { code: "ZM", name: "Zambia" }, { code: "ZW", name: "Zimbabwe" },
  { code: "MA", name: "Morocco" }, { code: "MW", name: "Malawi" },
  { code: "EG", name: "Egypt" }, { code: "SN", name: "Senegal" },
  { code: "CI", name: "Côte d'Ivoire" }, { code: "TN", name: "Tunisia" },
];

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800", expired: "bg-red-100 text-red-800",
  suspended: "bg-orange-100 text-orange-800", pending: "bg-yellow-100 text-yellow-800",
};

function SearchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [country, setCountry] = useState(searchParams.get("country") || "");
  const [status, setStatus] = useState(searchParams.get("status") || "");
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const search = useCallback(async (query: string, c: string, s: string, p: number) => {
    if (!query.trim() || query.length < 2) return;
    setLoading(true); setError(""); setSearched(true);
    const params = new URLSearchParams({ q: query, page: String(p) });
    if (c) params.set("country", c);
    if (s) params.set("status", s);
    try {
      const res = await fetch(`/api/search?${params}`);
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Search failed");
        setResults([]); setTotal(0);
      } else {
        setResults(data.results || []); setTotal(data.total || 0);
        router.replace(`/search?${params}`, { scroll: false });
      }
    } catch { setError("Network error"); }
    finally { setLoading(false); }
  }, [router]);

  useEffect(() => {
    const q0 = searchParams.get("q");
    if (q0) search(q0, searchParams.get("country") || "", searchParams.get("status") || "", 1);
  }, []); // eslint-disable-line

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setPage(1); search(q, country, status, 1);
  }

  const totalPages = Math.ceil(total / 50);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gray-900">Search Registrations</h1>

      <form onSubmit={handleSubmit} className="flex flex-wrap gap-2">
        <input value={q} onChange={e => setQ(e.target.value)}
          placeholder="Drug name or INN (e.g. amoxicillin)"
          className="flex-1 min-w-48 px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white" />
        <select value={country} onChange={e => setCountry(e.target.value)}
          className="px-3 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-600">
          {COUNTRIES.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)}
          className="px-3 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-600">
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
          <option value="suspended">Suspended</option>
          <option value="pending">Pending</option>
        </select>
        <button type="submit" disabled={loading || !q.trim()}
          className="px-6 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
          Search
        </button>
      </form>

      {error && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg px-4 py-3 text-sm text-orange-800">
          {error}
          {error.includes("limit") && (
            <Link href="/billing" className="ml-2 underline font-medium">Upgrade to Pro →</Link>
          )}
        </div>
      )}

      {loading && <div className="text-sm text-gray-400">Searching…</div>}

      {!loading && searched && !error && (
        <p className="text-sm text-gray-500">
          {total > 0 ? `${total.toLocaleString()} registration${total !== 1 ? "s" : ""} found` : "No results found"}
        </p>
      )}

      {!loading && results.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {["Product", "Market", "Reg. No.", "Holder", "Status", "Expires"].map(h => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-600 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {results.map((r) => (
                <tr key={r.id as string} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/record/${r.id}`} className="font-medium text-blue-600 hover:underline block">
                      {(r.brand_name as string) || (r.inn as string) || "—"}
                    </Link>
                    {Boolean(r.brand_name) && Boolean(r.inn) && <div className="text-xs text-gray-400">{r.inn as string}</div>}
                  </td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{r.country_name as string}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{(r.registration_no as string) || "—"}</td>
                  <td className="px-4 py-3 text-gray-700 max-w-48 truncate">{(r.holder as string) || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[r.status as string] || "bg-gray-100 text-gray-600"}`}>
                      {r.status as string}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                    {r.expiry_date ? new Date(r.expiry_date as string).toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" }) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex gap-2 justify-center">
          <button onClick={() => { const p = page - 1; setPage(p); search(q, country, status, p); }} disabled={page === 1}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50">Previous</button>
          <span className="px-4 py-2 text-sm text-gray-600">Page {page} of {totalPages}</span>
          <button onClick={() => { const p = page + 1; setPage(p); search(q, country, status, p); }} disabled={page >= totalPages}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50">Next</button>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="text-gray-400 text-sm">Loading…</div>}>
      <SearchContent />
    </Suspense>
  );
}
