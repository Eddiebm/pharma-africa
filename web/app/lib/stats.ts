import { sql } from "./db";

export type Stats = { total: number; display: string; markets: number };

export async function getStats(): Promise<Stats> {
  const rows = await sql`SELECT COUNT(*)::int AS total FROM registrations`;
  const total: number = rows[0].total;
  const rounded = Math.floor(total / 1000) * 1000;
  const display = rounded.toLocaleString("en-US") + "+";
  return { total, display, markets: 17 };
}
