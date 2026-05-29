"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function BillingContent() {
  const searchParams = useSearchParams();
  const [user, setUser] = useState<{ email: string; plan: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const success = searchParams.get("success");

  useEffect(() => {
    fetch("/api/auth/me").then(r => r.json()).then(d => setUser(d.user));
  }, []);

  async function upgrade() {
    setLoading(true);
    const res = await fetch("/api/billing/checkout", { method: "POST" });
    const d = await res.json();
    if (!res.ok) { alert(d.error || "Billing not available. Please contact support."); setLoading(false); return; }
    window.location.href = d.url;
  }

  const isPro = user?.plan === "pro" || user?.plan === "enterprise";

  return (
    <div className="space-y-6 max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900">Billing</h1>

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-800">
          Payment successful! Your account has been upgraded to Pro.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className={`bg-white border rounded-xl p-5 ${!isPro ? "border-blue-300 ring-2 ring-blue-100" : "border-gray-200"}`}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Free</h2>
            {user?.plan === "free" && <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">Current plan</span>}
          </div>
          <p className="text-3xl font-bold text-gray-900 mb-1">$0<span className="text-base font-normal text-gray-500">/mo</span></p>
          <ul className="text-sm text-gray-600 space-y-1.5 mt-4">
            <li>✓ 5 searches per day</li>
            <li>✓ All 15+ markets</li>
            <li className="text-gray-400">✗ Alerts</li>
            <li className="text-gray-400">✗ Portfolio tracker</li>
          </ul>
        </div>

        <div className={`bg-white border rounded-xl p-5 ${isPro ? "border-blue-300 ring-2 ring-blue-100" : "border-gray-200"}`}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Pro</h2>
            {isPro && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Current plan</span>}
          </div>
          <p className="text-3xl font-bold text-gray-900 mb-1">$199<span className="text-base font-normal text-gray-500">/mo</span></p>
          <ul className="text-sm text-gray-600 space-y-1.5 mt-4">
            <li>✓ Unlimited searches</li>
            <li>✓ All 15+ markets</li>
            <li>✓ Expiry alerts (90-day notice)</li>
            <li>✓ Portfolio tracker (CSV import)</li>
            <li>✓ Weekly digest emails</li>
            <li>✓ Monthly intelligence reports</li>
          </ul>
          {!isPro && (
            <button onClick={upgrade} disabled={loading}
              className="mt-5 w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {loading ? "Redirecting…" : "Upgrade to Pro"}
            </button>
          )}
        </div>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Enterprise</h2>
        <p className="text-sm text-gray-600">Need custom data exports, API access, or volume pricing? Contact us.</p>
        <a href="mailto:eddie@bannermanmenson.com" className="mt-3 inline-block text-sm text-blue-600 hover:underline">
          Contact sales →
        </a>
      </div>
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={<div className="text-sm text-gray-400">Loading…</div>}>
      <BillingContent />
    </Suspense>
  );
}
