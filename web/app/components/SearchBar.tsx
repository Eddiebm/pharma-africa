"use client";

import { useState, FormEvent } from "react";

const COUNTRIES = [
  { code: "", name: "All markets" },
  { code: "ZA", name: "South Africa" },
  { code: "NG", name: "Nigeria" },
  { code: "KE", name: "Kenya" },
  { code: "MW", name: "Malawi" },
  { code: "MA", name: "Morocco" },
  { code: "UG", name: "Uganda" },
  { code: "GH", name: "Ghana" },
  { code: "RW", name: "Rwanda" },
  { code: "ET", name: "Ethiopia" },
  { code: "TZ", name: "Tanzania" },
  { code: "ZM", name: "Zambia" },
  { code: "ZW", name: "Zimbabwe" },
  { code: "EG", name: "Egypt" },
];

interface Props {
  onSearch: (q: string, country: string) => void;
  loading: boolean;
}

export default function SearchBar({ onSearch, loading }: Props) {
  const [q, setQ] = useState("");
  const [country, setCountry] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSearch(q, country);
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Drug name or INN (e.g. amoxicillin, metformin)"
        className="flex-1 px-4 py-3 text-sm border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
        autoFocus
      />
      <select
        value={country}
        onChange={(e) => setCountry(e.target.value)}
        className="px-3 py-3 text-sm border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-600"
      >
        {COUNTRIES.map((c) => (
          <option key={c.code} value={c.code}>{c.name}</option>
        ))}
      </select>
      <button
        type="submit"
        disabled={loading || !q.trim()}
        className="px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Search
      </button>
    </form>
  );
}
