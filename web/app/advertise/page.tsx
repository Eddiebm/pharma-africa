export const runtime = "edge";

import type { Metadata } from "next";
import { getStats } from "../lib/stats";

export const metadata: Metadata = {
  title: "Advertise — AfricaRegulatory",
  description: "Reach pharmaceutical regulatory affairs teams, market access consultants, and pharma BD professionals across Africa.",
};

export default async function AdvertisePage() {
  const { display, markets } = await getStats();

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <a href="/" className="text-xl font-bold text-gray-900">AfricaRegulatory</a>
          <a href="mailto:hello@africaregulatory.com" className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
            Get in touch
          </a>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-16">

        {/* Hero */}
        <div className="mb-14">
          <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-3">Advertise</p>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Reach Africa's pharmaceutical regulatory professionals
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl">
            AfricaRegulatory is used by regulatory affairs teams, market access consultants, and pharma BD professionals tracking drug registrations across {markets} African markets.
          </p>
        </div>

        {/* Audience stats */}
        <div className="grid grid-cols-3 gap-6 mb-14">
          {[
            { value: display, label: "Drug registrations indexed" },
            { value: String(markets), label: "African markets covered" },
            { value: "Daily", label: "Data refreshed" },
          ].map(s => (
            <div key={s.label} className="bg-white border border-gray-200 rounded-xl p-6 text-center">
              <div className="text-3xl font-bold text-gray-900 mb-1">{s.value}</div>
              <div className="text-sm text-gray-500">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Who visits */}
        <div className="bg-white border border-gray-200 rounded-xl p-8 mb-10">
          <h2 className="text-xl font-semibold text-gray-900 mb-5">Who uses AfricaRegulatory</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { role: "Regulatory Affairs Managers", desc: "Tracking registration status and expiry across markets" },
              { role: "Market Access Consultants", desc: "Researching entry requirements for client products" },
              { role: "Pharma BD & Licensing Teams", desc: "Identifying registration gaps and opportunities" },
              { role: "Generics & Biosimilar Companies", desc: "Monitoring competitor registrations by market" },
            ].map(a => (
              <div key={a.role} className="flex gap-3">
                <div className="mt-1 w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-gray-900">{a.role}</div>
                  <div className="text-sm text-gray-500">{a.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Placements */}
        <h2 className="text-xl font-semibold text-gray-900 mb-5">Placements & pricing</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-14">
          {[
            {
              name: "Banner + Digest",
              price: "$500/mo",
              features: [
                "Homepage banner (above search results)",
                "Inclusion in weekly digest email",
                "Logo on /advertise page",
                "Cancel anytime",
              ],
            },
            {
              name: "Sponsored Market Guide",
              price: "$1,500 one-time",
              features: [
                "Branded PDF market entry guide",
                "Published under your company name",
                "Promoted in site + email for 30 days",
                "Linked from relevant market pages",
              ],
              featured: true,
            },
            {
              name: "Featured Listings",
              price: "$800/mo",
              features: [
                "Your service featured in search results",
                "Appears when users search your target markets",
                "\"Regulatory Partner\" badge on results page",
                "Cancel anytime",
              ],
            },
          ].map(p => (
            <div
              key={p.name}
              className={`rounded-xl border p-6 ${p.featured ? "border-blue-500 ring-1 ring-blue-500" : "border-gray-200 bg-white"}`}
            >
              {p.featured && (
                <div className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-3">Most popular</div>
              )}
              <div className="text-lg font-semibold text-gray-900 mb-1">{p.name}</div>
              <div className="text-2xl font-bold text-gray-900 mb-4">{p.price}</div>
              <ul className="space-y-2">
                {p.features.map(f => (
                  <li key={f} className="flex gap-2 text-sm text-gray-600">
                    <span className="text-blue-500 flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="bg-blue-600 rounded-2xl p-10 text-center text-white">
          <h2 className="text-2xl font-bold mb-2">Ready to reach Africa's regulatory community?</h2>
          <p className="text-blue-100 mb-6">
            Email us and we'll have your first placement live within 48 hours.
          </p>
          <a
            href="mailto:hello@africaregulatory.com?subject=Advertising inquiry"
            className="inline-block px-8 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition-colors"
          >
            hello@africaregulatory.com
          </a>
        </div>

      </div>
    </main>
  );
}
