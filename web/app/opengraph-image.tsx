import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "AfricaRegulatory — African Pharmaceutical Regulatory Intelligence";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #0f2744 0%, #1a4080 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", marginBottom: "32px" }}>
          <div
            style={{
              width: "12px",
              height: "48px",
              background: "#3b82f6",
              borderRadius: "4px",
              marginRight: "16px",
            }}
          />
          <span style={{ color: "#93c5fd", fontSize: "24px", fontWeight: 600, letterSpacing: "0.05em" }}>
            AFRICAREGULATORY.COM
          </span>
        </div>
        <div
          style={{
            color: "#ffffff",
            fontSize: "56px",
            fontWeight: 700,
            lineHeight: 1.15,
            maxWidth: "900px",
            marginBottom: "32px",
          }}
        >
          African Pharmaceutical Regulatory Intelligence
        </div>
        <div style={{ color: "#93c5fd", fontSize: "28px", fontWeight: 400 }}>
          161,000+ drug registrations · 17 African markets
        </div>
      </div>
    ),
    { ...size }
  );
}
