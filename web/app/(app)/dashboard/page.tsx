"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Stats {
  country_stats: { country_code: string; country_name: string; count: number }[];
  expiring_90_days: number;
  recent_searches: { query: string; country_code: string | null; created_at: string }[];
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/dashboard/stats")
      .then(r => r.json())
      .then(d => { setStats(d); setLoading(false); });
  }, []);

  if (loading) return <div className="text-gray-400 text-sm">Loading…</div>;
  if (!stats) return null;

  const maxCount = Math.max(...stats.country_stats.map(c => c.count), 1);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-sm text-gray-500">Total registrations</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">
            {stats.country_stats.reduce((s, c) => s + c.count, 0).toLocaleString()}
          </p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-sm text-gray-500">Markets covered</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{stats.country_stats.length}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-sm text-gray-500">Expiring in 90 days</p>
          <p className={`text-3xl font-bold mt-1 ${stats.expiring_90_days > 0 ? "text-orange-600" : "text-gray-900"}`}>
            {stats.expiring_90_days.toLocaleString()}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Registrations by country</h2>
          <div className="space-y-2">
            {stats.country_stats.map(c => (
              <div key={c.country_code} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-28 shrink-0">{c.country_name}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${(c.count / maxCount) * 100}%` }} />
                </div>
                <span className="text-xs text-gray-600 w-16 text-right">{c.count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Recent searches</h2>
          {stats.recent_searches.length === 0 ? (
            <p className="text-sm text-gray-400">
              No searches yet.{" "}
              <Link href="/search" className="text-blue-600 hover:underline">Start searching</Link>
            </p>
          ) : (
            <div className="space-y-2">
              {stats.recent_searches.map((s, i) => (
                <div key={i} className="flex items-center justify-between">
                  <Link href={`/search?q=${encodeURIComponent(s.query)}`}
                    className="text-sm text-blue-600 hover:underline truncate">
                    {s.query}
                  </Link>
                  <div className="flex items-center gap-2 ml-2 shrink-0">
                    {s.country_code && <span className="text-xs text-gray-400">{s.country_code}</span>}
                    <span className="text-xs text-gray-400">{new Date(s.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
