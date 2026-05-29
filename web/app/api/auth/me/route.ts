export const runtime = "edge";

import { verifyToken } from "@/app/lib/auth";

export async function GET(req: Request) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });
  return Response.json({ user });
}
