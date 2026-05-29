export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { verifyToken } from "@/app/lib/auth";

export async function GET(req: Request) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const sql = neon(dbUrl);

  const [countryStats, expiringStats, recentSearches] = await Promise.all([
    sql`
      SELECT country_code, COUNT(*)::int AS count
      FROM registrations
      GROUP BY country_code
      ORDER BY count DESC
      LIMIT 20
    `,
    sql`
      SELECT COUNT(*)::int AS count
      FROM registrations
      WHERE expiry_date BETWEEN NOW() AND NOW() + INTERVAL '90 days'
        AND status = 'active'
    `,
    sql`
      SELECT query, country_code, created_at
      FROM search_logs
      WHERE user_id = ${user.id}
      ORDER BY created_at DESC
      LIMIT 10
    `,
  ]);

  const COUNTRIES: Record<string, string> = {
    ZA: "South Africa", NG: "Nigeria", KE: "Kenya", GH: "Ghana", RW: "Rwanda",
    TZ: "Tanzania", UG: "Uganda", ET: "Ethiopia", ZM: "Zambia", ZW: "Zimbabwe",
    MA: "Morocco", MW: "Malawi", EG: "Egypt", SN: "Senegal", CI: "Côte d'Ivoire", TN: "Tunisia",
  };

  return Response.json({
    country_stats: countryStats.map((r: Record<string, unknown>) => ({
      country_code: r.country_code,
      country_name: COUNTRIES[r.country_code as string] || r.country_code,
      count: r.count,
    })),
    expiring_90_days: expiringStats[0]?.count ?? 0,
    recent_searches: recentSearches,
  });
}
