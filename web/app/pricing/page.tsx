"use client";

import Link from "next/link";
import { useState } from "react";

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "For individuals exploring African regulatory data.",
    cta: "Start free",
    href: "/signup",
    highlight: false,
    external: false,
    features: [
      { text: "5 searches per day", included: true },
      { text: "All 16 markets", included: true },
      { text: "Drug record detail pages", included: true },
      { text: "WHO Prequalification lookup", included: true },
      { text: "Expiry alerts", included: false },
      { text: "Portfolio tracker", included: false },
      { text: "Weekly digest emails", included: false },
      { text: "Monthly intelligence reports", included: false },
      { text: "API access", included: false },
    ],
  },
  {
    name: "Pro",
    price: "$199",
    period: "/ month",
    description: "For regulatory affairs professionals and market access teams.",
    cta: "Start Pro",
    href: "/signup?plan=pro",
    highlight: true,
    badge: "Most popular",
    external: false,
    features: [
      { text: "Unlimited searches", included: true },
      { text: "All 16 markets", included: true },
      { text: "Drug record detail pages", included: true },
      { text: "WHO Prequalification lookup", included: true },
      { text: "Expiry alerts (90-day advance notice)", included: true },
      { text: "Portfolio tracker (CSV import)", included: true },
      { text: "Weekly digest emails", included: true },
      { text: "Monthly intelligence reports (PDF)", included: true },
      { text: "API access", included: false },
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For regulatory teams at pharma companies and consultancies.",
    cta: "Contact sales →",
    href: "mailto:hello@africaregulatory.com?subject=AfricaRegulatory Enterprise Inquiry",
    highlight: false,
    external: true,
    features: [
      { text: "Everything in Pro", included: true },
      { text: "Unlimited seats", included: true },
      { text: "REST API access", included: true },
      { text: "Custom data exports", included: true },
      { text: "Dedicated account manager", included: true },
      { text: "Bespoke market coverage", included: true },
      { text: "Priority support", included: true },
      { text: "99.9% SLA", included: true },
      { text: "Custom contract & invoicing", included: true },
    ],
  },
];

const FAQS = [
  {
    q: "How often is the data updated?",
    a: "Our scrapers run nightly against the official regulatory authority websites for all 16 markets. Most markets update within 24 hours of a new approval or status change.",
  },
  {
    q: "Which countries are covered?",
    a: "Nigeria (NAFDAC), South Africa (SAHPRA), Kenya (PPB), Ghana (FDA), Egypt (EDA), Morocco (DMP), Tunisia (DPM), Côte d'Ivoire (AIRP), Senegal (ARP), Uganda (NDA), Tanzania (TMDA), Malawi (PMRA), Zambia (ZAMRA), Zimbabwe (MCAZ), Rwanda (RDA), and WHO Prequalification.",
  },
  {
    q: "What is the portfolio tracker?",
    a: "Upload a CSV of your drug portfolio (INN or brand name). AfricaRegulatory maps each drug to its registration status across all tracked markets and alerts you 90 days before any registration expires.",
  },
  {
    q: "Can I get a trial before paying?",
    a: "Yes — the free tier gives you full access to search and records with a 5 searches/day limit. No credit card required.",
  },
  {
    q: "What's in the monthly intelligence report?",
    a: "A professionally formatted PDF covering: new approvals by market, expiry watch, top registration holders, WHO Prequalification updates, and an AI-written executive summary with key trends. Published on the 1st of each month.",
  },
  {
    q: "How does Enterprise pricing work?",
    a: "Enterprise is priced based on your team size, markets, and data requirements. Email hello@africaregulatory.com to get a quote — most deals close within a week.",
  },
];

export default function PricingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

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
            <Link href="/reports" className="text-sm text-gray-600 hover:text-gray-900">Reports</Link>
            <Link href="/pricing" className="text-sm font-medium text-blue-600">Pricing</Link>
            <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">Sign in</Link>
            <Link href="/signup" className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">Sign up free</Link>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-16">

        {/* Hero */}
        <div className="text-center mb-14">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Regulatory intelligence that pays for itself
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            One missed registration expiry can cost hundreds of thousands in market access delays.
            AfricaRegulatory Pro alerts you 90 days in advance across all 16 markets.
          </p>
        </div>

        {/* Plans */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
          {PLANS.map(plan => (
            <div key={plan.name} className={`bg-white rounded-2xl border flex flex-col ${plan.highlight ? "border-blue-500 shadow-lg shadow-blue-100 relative" : "border-gray-200"}`}>
              {plan.badge && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                  <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">{plan.badge}</span>
                </div>
              )}
              <div className={`p-6 ${plan.highlight ? "pt-8" : ""}`}>
                <h2 className="text-lg font-bold text-gray-900 mb-1">{plan.name}</h2>
                <p className="text-sm text-gray-500 mb-4 min-h-[40px]">{plan.description}</p>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                  {plan.period && <span className="text-gray-400 text-sm">{plan.period}</span>}
                </div>
                {plan.external ? (
                  <a
                    href={plan.href}
                    className="block w-full text-center py-2.5 rounded-lg text-sm font-semibold transition-colors bg-gray-900 text-white hover:bg-gray-700"
                  >
                    {plan.cta}
                  </a>
                ) : (
                  <Link
                    href={plan.href}
                    className={`block w-full text-center py-2.5 rounded-lg text-sm font-semibold transition-colors ${plan.highlight ? "bg-blue-600 text-white hover:bg-blue-700" : "bg-gray-100 text-gray-800 hover:bg-gray-200"}`}
                  >
                    {plan.cta}
                  </Link>
                )}
              </div>
              <div className="px-6 pb-6 flex-1">
                <div className="border-t border-gray-100 pt-5 space-y-3">
                  {plan.features.map(f => (
                    <div key={f.text} className="flex items-start gap-2.5">
                      <span className={`mt-0.5 text-sm shrink-0 ${f.included ? "text-blue-500" : "text-gray-300"}`}>
                        {f.included ? "✓" : "✗"}
                      </span>
                      <span className={`text-sm ${f.included ? "text-gray-700" : "text-gray-400"}`}>{f.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Trust signals */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
          {[
            ["96,000+", "Drug registrations"],
            ["16", "African markets"],
            ["19", "Regulatory bodies"],
            ["Daily", "Data updates"],
          ].map(([n, l]) => (
            <div key={l} className="bg-white border border-gray-200 rounded-xl p-5 text-center">
              <div className="text-2xl font-bold text-gray-900">{n}</div>
              <div className="text-xs text-gray-500 mt-1">{l}</div>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Frequently asked questions</h2>
          <div className="space-y-3">
            {FAQS.map((faq, i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between px-5 py-4 text-left"
                >
                  <span className="font-medium text-gray-900 text-sm">{faq.q}</span>
                  <span className={`text-gray-400 transition-transform text-lg ${openFaq === i ? "rotate-45" : ""}`}>+</span>
                </button>
                {openFaq === i && (
                  <div className="px-5 pb-4 text-sm text-gray-600 leading-relaxed border-t border-gray-100 pt-3">
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
