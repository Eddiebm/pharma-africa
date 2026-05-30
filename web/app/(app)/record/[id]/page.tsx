"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

const ERROR_TYPES = [
  { value: "wrong_status",  label: "Status is wrong (active / expired / suspended)" },
  { value: "wrong_expiry",  label: "Expiry date is incorrect" },
  { value: "wrong_holder",  label: "Holder or company name is wrong" },
  { value: "not_found",     label: "Can't find this on the official registry" },
  { value: "duplicate",     label: "This is a duplicate record" },
  { value: "other",         label: "Something else" },
];

function ReportErrorWidget({ registrationId }: { registrationId: string }) {
  const [open, setOpen] = useState(false);
  const [errorType, setErrorType] = useState("");
  const [notes, setNotes] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "done" | "error">("idle");

  async function submit() {
    if (!errorType) return;
    setStatus("sending");
    const res = await fetch(`/api/record/${registrationId}/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error_type: errorType, notes: notes || undefined, reporter_email: email || undefined }),
    });
    setStatus(res.ok ? "done" : "error");
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
        Report an error with this record
      </button>
    );
  }

  if (status === "done") {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
        Thanks — we'll review this and correct it within 48 hours.
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Report an error</h3>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
      </div>

      <div className="space-y-2">
        <p className="text-xs text-gray-500">What's wrong?</p>
        {ERROR_TYPES.map(t => (
          <label key={t.value} className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="radio"
              name="error_type"
              value={t.value}
              checked={errorType === t.value}
              onChange={() => setErrorType(t.value)}
              className="accent-blue-600"
            />
            <span className="text-sm text-gray-700">{t.label}</span>
          </label>
        ))}
      </div>

      <textarea
        value={notes}
        onChange={e => setNotes(e.target.value)}
        placeholder="Additional details (optional)"
        rows={2}
        className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
      />

      <input
        type="email"
        value={email}
        onChange={e => setEmail(e.target.value)}
        placeholder="Your email (optional — we'll notify you when fixed)"
        className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {status === "error" && <p className="text-xs text-red-500">Something went wrong — please try again.</p>}

      <button
        onClick={submit}
        disabled={!errorType || status === "sending"}
        className="w-full py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {status === "sending" ? "Submitting…" : "Submit report"}
      </button>
    </div>
  );
}

const COUNTRIES: Record<string, string> = {
  ZA:"South Africa",NG:"Nigeria",KE:"Kenya",GH:"Ghana",RW:"Rwanda",TZ:"Tanzania",
  UG:"Uganda",ET:"Ethiopia",ZM:"Zambia",ZW:"Zimbabwe",MA:"Morocco",MW:"Malawi",
  EG:"Egypt",SN:"Senegal",CI:"Côte d'Ivoire",TN:"Tunisia",
};

const STATUS_COLORS: Record<string, string> = {
  active:"bg-green-100 text-green-800",expired:"bg-red-100 text-red-800",
  suspended:"bg-orange-100 text-orange-800",pending:"bg-yellow-100 text-yellow-800",
};

function fmt(d: string | null) {
  if (!d) return "—";
  const date = new Date(d);
  if (date.getFullYear() < 1990) return "—";
  return date.toLocaleDateString("en-GB", { day:"2-digit", month:"long", year:"numeric" });
}

export default function RecordPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<{ record: Record<string, unknown>; who_prequalified: Record<string, unknown>[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/record/${id}`)
      .then(async r => {
        if (r.status === 401) { router.push("/login"); return; }
        if (!r.ok) { router.push("/search"); return; }
        setData(await r.json());
      })
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) return <div className="text-gray-400 text-sm">Loading…</div>;
  if (!data) return null;
  const { record: r, who_prequalified } = data;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="text-sm text-gray-500">
        <Link href="/search" className="hover:text-gray-900">← Search</Link>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{(r.brand_name as string) || (r.inn as string) || "Unknown"}</h1>
            {Boolean(r.brand_name) && Boolean(r.inn) && <p className="text-gray-500 mt-1">{r.inn as string}</p>}
          </div>
          <span className={`shrink-0 px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[r.status as string] || "bg-gray-100 text-gray-600"}`}>
            {r.status as string}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 pt-2">
          {([
            ["Market", COUNTRIES[r.country_code as string] || r.country_code],
            ["Registration No.", r.registration_no || "—"],
            ["Holder", r.holder || "—"],
            ["Local Agent", r.local_agent || "—"],
            ["Dosage Forms", Array.isArray(r.dosage_forms) ? (r.dosage_forms as string[]).join(", ") || "—" : "—"],
            ["Expiry Date", fmt(r.expiry_date as string | null)],
            ["Source Type", r.source_type || "—"],
            ["Last Updated", fmt(r.last_verified as string | null)],
          ] as [string, unknown][]).map(([label, value]) => (
            <div key={label}>
              <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
              <p className="text-sm text-gray-900 mt-0.5 break-words">{String(value)}</p>
            </div>
          ))}
        </div>

        {Boolean(r.source_url) && (
          <div className="pt-2">
            <a href={r.source_url as string} target="_blank" rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline">View source →</a>
          </div>
        )}
      </div>

      {who_prequalified.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">WHO Prequalification</h2>
          <div className="space-y-3">
            {who_prequalified.map((w, i) => (
              <div key={i} className="text-sm">
                <p className="font-medium text-gray-900">{w.product_name as string}</p>
                <p className="text-gray-500">{w.manufacturer as string} · {w.dosage_form as string} · {w.strength as string}</p>
                {Boolean(w.who_ref) && <p className="text-xs text-gray-400 mt-0.5">{w.who_ref as string}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <ReportErrorWidget registrationId={id} />
    </div>
  );
}
