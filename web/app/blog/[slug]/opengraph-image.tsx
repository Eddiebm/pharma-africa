import { ImageResponse } from "next/og";
import { neon } from "@neondatabase/serverless";

export const runtime = "edge";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const CATEGORY_LABELS: Record<string, string> = {
  "expiry-watch": "Expiry Watch",
  "new-registrations": "New Registrations",
  "generic-opportunities": "Generic Opportunities",
  "market-entry": "Market Entry Intelligence",
};

export default async function OGImage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let title = "AfricaRegulatory Intelligence Report";
  let category = "";

  const dbUrl = process.env.DATABASE_URL;
  if (dbUrl) {
    const sql = neon(dbUrl);
    const [post] = await sql`SELECT title, category FROM blog_posts WHERE slug = ${slug}`;
    if (post) {
      title = post.title as string;
      category = CATEGORY_LABELS[post.category as string] || "";
    }
  }

  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #0f2744 0%, #1a4080 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center" }}>
          <div style={{ width: "10px", height: "40px", background: "#3b82f6", borderRadius: "4px", marginRight: "14px" }} />
          <span style={{ color: "#93c5fd", fontSize: "22px", fontWeight: 600, letterSpacing: "0.05em" }}>
            AFRICAREGULATORY.COM
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {category ? (
            <div
              style={{
                background: "rgba(59,130,246,0.2)",
                border: "1px solid rgba(59,130,246,0.4)",
                borderRadius: "6px",
                padding: "6px 16px",
                color: "#93c5fd",
                fontSize: "18px",
                fontWeight: 600,
                width: "fit-content",
              }}
            >
              {category}
            </div>
          ) : null}
          <div style={{ color: "#ffffff", fontSize: "48px", fontWeight: 700, lineHeight: 1.2, maxWidth: "950px" }}>
            {title}
          </div>
        </div>

        <div style={{ color: "#64748b", fontSize: "20px" }}>
          African Pharmaceutical Regulatory Intelligence · 95,000+ registrations
        </div>
      </div>
    ),
    { ...size }
  );
}
