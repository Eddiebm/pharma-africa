export const runtime = "edge";

import { neon } from "@neondatabase/serverless";

export async function POST(req: Request) {
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) return new Response("Webhook secret not configured", { status: 503 });

  const body = await req.text();
  const sig = req.headers.get("stripe-signature") || "";

  const valid = await verifyStripeSignature(body, sig, webhookSecret);
  if (!valid) return new Response("Invalid signature", { status: 400 });

  let event: { type: string; data: { object: Record<string, unknown> } };
  try { event = JSON.parse(body); } catch { return new Response("Invalid JSON", { status: 400 }); }

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return new Response("DB not configured", { status: 500 });
  const sql = neon(dbUrl);

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    const userId = (session.metadata as Record<string, string> | null)?.user_id;
    if (userId) {
      await sql`
        UPDATE users
        SET plan = 'pro', stripe_customer_id = ${session.customer as string}
        WHERE id = ${userId}
      `;
    }
  }

  if (event.type === "customer.subscription.deleted") {
    const sub = event.data.object;
    const customerId = sub.customer as string;
    if (customerId) {
      await sql`UPDATE users SET plan = 'free' WHERE stripe_customer_id = ${customerId}`;
    }
  }

  if (event.type === "customer.subscription.updated") {
    const sub = event.data.object;
    const customerId = sub.customer as string;
    const status = sub.status as string;
    if (customerId) {
      // active / trialing = keep pro; canceled / unpaid / past_due (after grace) = downgrade
      const plan = (status === "active" || status === "trialing") ? "pro" : "free";
      await sql`UPDATE users SET plan = ${plan} WHERE stripe_customer_id = ${customerId}`;
    }
  }

  return new Response("ok");
}

async function verifyStripeSignature(payload: string, sigHeader: string, secret: string): Promise<boolean> {
  try {
    const parts = sigHeader.split(",").reduce<Record<string, string>>((acc, part) => {
      const [k, v] = part.split("=");
      acc[k] = v;
      return acc;
    }, {});
    const ts = parts["t"];
    const v1 = parts["v1"];
    if (!ts || !v1) return false;

    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
    const data = new TextEncoder().encode(`${ts}.${payload}`);
    const sig = await crypto.subtle.sign("HMAC", key, data);
    const computed = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, "0")).join("");
    return computed === v1;
  } catch {
    return false;
  }
}
