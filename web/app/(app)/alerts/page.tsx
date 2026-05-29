"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const ALL_COUNTRIES = [
  { code: "ZA", name: "South Africa" }, { code: "NG", name: "Nigeria" },
  { code: "KE", name: "Kenya" }, { code: "GH", name: "Ghana" },
  { code: "RW", name: "Rwanda" }, { code: "TZ", name: "Tanzania" },
  { code: "UG", name: "Uganda" }, { code: "ET", name: "Ethiopia" },
  { code: "ZM", name: "Zambia" }, { code: "ZW", name: "Zimbabwe" },
  { code: "MA", name: "Morocco" }, { code: "MW", name: "Malawi" },
  { code: "EG", name: "Egypt" }, { code: "SN", name: "Senegal" },
  { code: "CI", name: "Côte d'Ivoire" }, { code: "TN", name: "Tunisia" },
];

interface Sub {
  id: string;
  country_codes: string[];
  expiry_days_threshold: number;
  active: boolean;
  created_at: string;
}

export default function AlertsPage() {
  const [subs, setSubs] = useState<Sub[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPro, setIsPro] = useState<boolean | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [threshold, setThreshold] = useState(90);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([
      fetch("/api/auth/me").then(r => r.json()),
      fetch("/api/alerts").then(r => r.json()),
    ]).then(([me, alertData]) => {
      setIsPro(me.user?.plan !== "free");
      setSubs(alertData.subscriptions || []);
      setLoading(false);
    });
  }, []);

  async function createAlert() {
    if (selected.length === 0) return;
    setSaving(true); setMessage("");
    const res = await fetch("/api/alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ country_codes: selected, expiry_days_threshold: threshold }),
    });
    const d = await res.json();
    if (!res.ok) setMessage(d.error || "Failed to create alert");
    else { setSubs(s => [...s, d.subscription]); setSelected([]); setMessage("Alert created"); }
    setSaving(false);
  }

  async function deleteAlert(id: string) {
    await fetch(`/api/alerts/${id}`, { method: "DELETE" });
    setSubs(s => s.filter(a => a.id !== id));
  }

  async function toggleActive(sub: Sub) {
    const res = await fetch(`/api/alerts/${sub.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active: !sub.active }),
    });
    const d = await res.json();
    if (res.ok) setSubs(s => s.map(a => a.id === sub.id ? d.subscription : a));
  }

  function toggleCountry(code: string) {
    setSelected(s => s.includes(code) ? s.filter(c => c !== code) : [...s, code]);
  }

  if (loading) return <div className="text-sm text-gray-400">Loading…</div>;

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Expiry Alerts</h1>

      {!isPro && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
          <p className="text-sm text-blue-800 font-medium">Alerts require a Pro plan</p>
          <p className="text-sm text-blue-600 mt-1">Upgrade to receive email alerts when registrations are about to expire.</p>
          <Link href="/billing" className="mt-3 inline-block px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
            Upgrade to Pro →
          </Link>
        </div>
      )}

      {isPro && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">Create new alert</h2>
          <div>
            <p className="text-xs text-gray-500 mb-2">Select countries to monitor</p>
            <div className="flex flex-wrap gap-2">
              {ALL_COUNTRIES.map(c => (
                <button key={c.code} onClick={() => toggleCountry(c.code)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                    selected.includes(c.code) ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}>{c.name}</button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-700">Alert me</label>
            <select value={threshold} onChange={e => setThreshold(Number(e.target.value))}
              className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value={30}>30 days</option>
              <option value={60}>60 days</option>
              <option value={90}>90 days</option>
              <option value={180}>180 days</option>
            </select>
            <label className="text-sm text-gray-700">before expiry</label>
          </div>
          {message && <p className={`text-sm ${message.includes("Failed") ? "text-red-600" : "text-green-600"}`}>{message}</p>}
          <button onClick={createAlert} disabled={saving || selected.length === 0}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {saving ? "Saving…" : "Create alert"}
          </button>
        </div>
      )}

      {subs.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Active alerts</h2>
          {subs.map(sub => {
            const names = sub.country_codes.map(cc => ALL_COUNTRIES.find(c => c.code === cc)?.name || cc);
            return (
              <div key={sub.id} className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">{names.join(", ")}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{sub.expiry_days_threshold} days before expiry</p>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => toggleActive(sub)}
                    className={`px-2.5 py-1 rounded-full text-xs font-medium ${sub.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {sub.active ? "Active" : "Paused"}
                  </button>
                  <button onClick={() => deleteAlert(sub.id)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
