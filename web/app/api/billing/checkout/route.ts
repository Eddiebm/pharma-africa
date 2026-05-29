export const runtime = "edge";

import { verifyToken } from "@/app/lib/auth";

export async function POST(req: Request) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  const priceId = process.env.STRIPE_PRO_PRICE_ID;
  if (!stripeKey || !priceId) {
    return Response.json({ error: "Billing not configured" }, { status: 503 });
  }

  const { origin } = new URL(req.url);

  const res = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${stripeKey}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      "customer_email": user.email,
      "mode": "subscription",
      "line_items[0][price]": priceId,
      "line_items[0][quantity]": "1",
      "success_url": `${origin}/billing?success=1`,
      "cancel_url": `${origin}/billing`,
      "metadata[user_id]": user.id,
    }),
  });

  if (!res.ok) {
    console.error("Stripe error", await res.text());
    return Response.json({ error: "Failed to create checkout session" }, { status: 500 });
  }

  const session = await res.json() as { url: string };
  return Response.json({ url: session.url });
}
