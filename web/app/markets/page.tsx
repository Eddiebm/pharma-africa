export const runtime = "edge";

import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "African Pharmaceutical Markets — AfricaRegulatory",
  description: "Browse drug registration data for 16 African pharmaceutical markets. Nigeria, South Africa, Kenya, Ghana, Egypt, Morocco, and more.",
  alternates: { canonical: "https://africaregulatory.com/markets" },
};

const MARKETS = [
  { name: "South Africa",   code: "ZA", regulator: "SAHPRA",    slug: "south-africa",   registrations: "18,000+" },
  { name: "Ghana",          code: "GH", regulator: "FDA Ghana", slug: "ghana",          registrations: "15,000+" },
  { name: "Nigeria",        code: "NG", regulator: "NAFDAC",    slug: "nigeria",        registrations: "8,700+"  },
  { name: "Côte d'Ivoire",  code: "CI", regulator: "AIRP",      slug: "cote-divoire",   registrations: "7,100+"  },
  { name: "Senegal",        code: "SN", regulator: "ARP",       slug: "senegal",        registrations: "6,900+"  },
  { name: "Malawi",         code: "MW", regulator: "PMRA",      slug: "malawi",         registrations: "6,400+"  },
  { name: "Tunisia",        code: "TN", regulator: "DPM",       slug: "tunisia",        registrations: "6,000+"  },
  { name: "Morocco",        code: "MA", regulator: "DMP",       slug: "morocco",        registrations: "5,900+"  },
  { name: "Zambia",         code: "ZM", regulator: "ZAMRA",     slug: "zambia",         registrations: "4,300+"  },
  { name: "Uganda",         code: "UG", regulator: "NDA",       slug: "uganda",         registrations: "3,900+"  },
  { name: "Zimbabwe",       code: "ZW", regulator: "MCAZ",      slug: "zimbabwe",       registrations: "3,800+"  },
  { name: "Kenya",          code: "KE", regulator: "PPB",       slug: "kenya",          registrations: "2,500+"  },
  { name: "Rwanda",         code: "RW", regulator: "RDA",       slug: "rwanda",         registrations: "2,400+"  },
  { name: "Egypt",          code: "EG", regulator: "EDA",       slug: "egypt",          registrations: "500+"    },
  { name: "Tanzania",       code: "TZ", regulator: "TMDA",      slug: "tanzania",       registrations: "Coming soon" },
  { name: "Ethiopia",       code: "ET", regulator: "EFDA",      slug: "ethiopia",       registrations: "Coming soon" },
];

export default function MarketsPage() {
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
            <Link href="/pricing" className="text-sm text-gray-600 hover:text-gray-900">Pricing</Link>
            <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">Sign in</Link>
            <Link href="/signup" className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">Sign up free</Link>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">African Pharmaceutical Markets</h1>
          <p className="text-lg text-gray-500 max-w-2xl">
            93,000+ drug registrations across 16 markets — searchable, filterable, and continuously updated from official regulatory authority sources.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {MARKETS.map(m => (
            <Link
              key={m.slug}
              href={`/markets/${m.slug}`}
              className="bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-sm transition-all group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">{m.name}</h2>
                  <p className="text-sm text-gray-500 mt-0.5">{m.regulator}</p>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-semibold ${m.registrations === "Coming soon" ? "text-gray-400" : "text-gray-700"}`}>{m.registrations}</div>
                  {m.registrations !== "Coming soon" && <div className="text-xs text-gray-400">registrations</div>}
                </div>
              </div>
            </Link>
          ))}
        </div>

        <div className="mt-12 bg-blue-50 border border-blue-100 rounded-xl p-6 text-center">
          <p className="font-semibold text-gray-900 mb-1">Search across all 16 markets at once</p>
          <p className="text-sm text-gray-500 mb-4">Filter by drug name, INN, registration holder, status, and expiry date</p>
          <Link href="/signup" className="inline-block px-6 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors">
            Start searching free →
          </Link>
        </div>
      </div>
    </div>
  );
}
