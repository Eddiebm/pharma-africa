export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { verifyToken } from "@/app/lib/auth";

const COUNTRIES = ["ZA","NG","KE","GH","RW","TZ","UG","ET","ZM","ZW","MA","MW","EG","SN","CI","TN"];
const COUNTRY_NAMES: Record<string, string> = {
  ZA:"South Africa",NG:"Nigeria",KE:"Kenya",GH:"Ghana",RW:"Rwanda",TZ:"Tanzania",
  UG:"Uganda",ET:"Ethiopia",ZM:"Zambia",ZW:"Zimbabwe",MA:"Morocco",MW:"Malawi",
  EG:"Egypt",SN:"Senegal",CI:"Côte d'Ivoire",TN:"Tunisia",
};

export async function GET(req: Request) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const sql = neon(dbUrl);
  const portfolio = await sql`
    SELECT id, drug_name, inn FROM portfolios WHERE user_id = ${user.id} ORDER BY drug_name
  `;

  if (portfolio.length === 0) return Response.json({ matrix: [], countries: COUNTRIES.map(c => ({ code: c, name: COUNTRY_NAMES[c] })) });

  // For each portfolio item, find registrations across all countries
  const matrix = await Promise.all(portfolio.map(async (item: Record<string, unknown>) => {
    const searchTerm = `%${item.inn || item.drug_name}%`;
    const regs = await sql`
      SELECT country_code, status, expiry_date, registration_no
      FROM registrations
      WHERE (inn ILIKE ${searchTerm} OR brand_name ILIKE ${searchTerm})
      ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END
    `;

    const byCountry: Record<string, { status: string; expiry_date: string | null; registration_no: string | null }> = {};
    for (const reg of regs as Record<string, unknown>[]) {
      const cc = reg.country_code as string;
      if (!byCountry[cc]) {
        byCountry[cc] = { status: reg.status as string, expiry_date: reg.expiry_date as string | null, registration_no: reg.registration_no as string | null };
      }
    }

    return {
      id: item.id,
      drug_name: item.drug_name,
      inn: item.inn,
      countries: COUNTRIES.map(cc => ({
        code: cc,
        ...(byCountry[cc] || { status: "not_found", expiry_date: null, registration_no: null }),
      })),
    };
  }));

  return Response.json({ matrix, countries: COUNTRIES.map(c => ({ code: c, name: COUNTRY_NAMES[c] })) });
}
