"use client";

import { useState, useRef, useEffect } from "react";

interface MatrixRow {
  id: string;
  drug_name: string;
  inn: string | null;
  countries: { code: string; status: string; expiry_date: string | null; registration_no: string | null }[];
}

interface MatrixData {
  matrix: MatrixRow[];
  countries: { code: string; name: string }[];
}

const STATUS_COLOR: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  expired: "bg-red-100 text-red-700",
  suspended: "bg-orange-100 text-orange-700",
  pending: "bg-yellow-100 text-yellow-700",
  not_found: "bg-gray-100 text-gray-400",
};

export default function PortfolioPage() {
  const [data, setData] = useState<MatrixData | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch("/api/portfolio/status").then(r => r.json()).then(d => { setData(d); setLoading(false); });
  }, []);

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true); setMessage("");
    const text = await file.text();
    const res = await fetch("/api/portfolio/upload", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: text,
    });
    const d = await res.json();
    if (!res.ok) { setMessage(d.error || "Upload failed"); }
    else {
      setMessage(`Imported ${d.imported} drugs`);
      const refreshed = await fetch("/api/portfolio/status").then(r => r.json());
      setData(refreshed);
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  }

  const downloadTemplate = () => {
    const csv = "drug_name,inn\nAmoxicillin Capsules,amoxicillin\nMetformin Tablets,metformin\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "portfolio_template.csv";
    a.click();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Portfolio Tracker</h1>
        <button onClick={downloadTemplate} className="text-sm text-blue-600 hover:underline">
          Download template CSV
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Upload your drug portfolio</h2>
        <p className="text-xs text-gray-500">CSV with columns: drug_name, inn. Uploading replaces your current portfolio.</p>
        <div className="flex gap-3">
          <input ref={fileRef} type="file" accept=".csv" className="flex-1 text-sm text-gray-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200" />
          <button onClick={handleUpload} disabled={uploading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </div>
        {message && <p className={`text-sm ${message.includes("failed") || message.includes("error") ? "text-red-600" : "text-green-600"}`}>{message}</p>}
      </div>

      {loading && <div className="text-sm text-gray-400">Loading portfolio…</div>}

      {!loading && data && data.matrix.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-2">No portfolio yet</p>
          <p className="text-sm">Upload a CSV to see your drug registration matrix across all markets.</p>
        </div>
      )}

      {!loading && data && data.matrix.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-x-auto shadow-sm">
          <table className="text-xs">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-3 font-medium text-gray-600 whitespace-nowrap sticky left-0 bg-gray-50 min-w-40">Drug</th>
                {data.countries.map(c => (
                  <th key={c.code} className="text-center px-2 py-3 font-medium text-gray-600 whitespace-nowrap min-w-24">{c.name}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.matrix.map(row => (
                <tr key={row.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 sticky left-0 bg-white">
                    <div className="font-medium text-gray-900">{row.drug_name}</div>
                    {row.inn && <div className="text-gray-400">{row.inn}</div>}
                  </td>
                  {row.countries.map(c => (
                    <td key={c.code} className="px-2 py-3 text-center">
                      <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${STATUS_COLOR[c.status] || STATUS_COLOR.not_found}`}>
                        {c.status === "not_found" ? "—" : c.status}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
