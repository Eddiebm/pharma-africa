export const runtime = "edge";

import { getStats } from "../../lib/stats";

export async function GET() {
  const stats = await getStats();
  return Response.json(stats);
}
