"use client";

import { Registration } from "../page";

const STATUS_COLORS: Record<string, string> = {
  active:    "bg-green-100 text-green-800",
  expired:   "bg-red-100 text-red-800",
  suspended: "bg-orange-100 text-orange-800",
  pending:   "bg-yellow-100 text-yellow-800",
  unknown:   "bg-gray-100 text-gray-600",
};

function formatDate(d: string | null) {
  if (!d) return "—";
  const date = new Date(d);
  if (date.getFullYear() < 1990) return "—";
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function isExpiringSoon(d: string | null) {
  if (!d) return false;
  const months6 = new Date();
  months6.setMonth(months6.getMonth() + 6);
  return new Date(d) < months6 && new Date(d) > new Date();
}

interface Props { results: Registration[] }

export default function ResultsTable({ results }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200">
            <th className="text-left px-4 py-3 font-medium text-gray-600">Product</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Market</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Reg. No.</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Holder</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Expires</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {results.map((r) => (
            <tr key={r.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3">
                <div className="font-medium text-gray-900">{r.brand_name || r.inn || "—"}</div>
                {r.brand_name && r.inn && (
                  <div className="text-xs text-gray-400 mt-0.5">{r.inn}</div>
                )}
                {r.dosage_forms?.length > 0 && (
                  <div className="text-xs text-gray-400">{r.dosage_forms.join(", ")}</div>
                )}
              </td>
              <td className="px-4 py-3 text-gray-700">{r.country_name}</td>
              <td className="px-4 py-3 font-mono text-xs text-gray-600">{r.registration_no || "—"}</td>
              <td className="px-4 py-3 text-gray-700 max-w-[200px] truncate" title={r.holder || ""}>{r.holder || "—"}</td>
              <td className="px-4 py-3">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[r.status] || STATUS_COLORS.unknown}`}>
                  {r.status}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className={isExpiringSoon(r.expiry_date) ? "text-orange-600 font-medium" : "text-gray-600"}>
                  {formatDate(r.expiry_date)}
                  {isExpiringSoon(r.expiry_date) && <span className="ml-1 text-xs">⚠️</span>}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {results.length === 100 && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-400">
          Showing first 100 results. Narrow your search for more specific results.
        </div>
      )}
    </div>
  );
}
