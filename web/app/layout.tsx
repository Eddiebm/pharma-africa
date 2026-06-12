import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { getStats } from "./lib/stats";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export async function generateMetadata(): Promise<Metadata> {
  const { display, markets } = await getStats();
  return {
    title: "AfricaRegulatory — African Pharmaceutical Regulatory Intelligence",
    description: `Search ${display} drug registrations across ${markets} African markets. Track expiry dates, new approvals, and market opportunities.`,
    metadataBase: new URL("https://africaregulatory.com"),
    verification: {
      google: "E0ijiNWr8RmygHW3iS0Ave61YZQAaxg34Bw8EX3MnvU",
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
