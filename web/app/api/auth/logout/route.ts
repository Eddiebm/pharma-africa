export const runtime = "edge";

import { sessionCookieClear } from "@/app/lib/auth";

export async function POST() {
  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json", "Set-Cookie": sessionCookieClear() },
  });
}
