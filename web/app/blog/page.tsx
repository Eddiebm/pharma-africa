export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Blog — AfriReg | African Pharmaceutical Regulatory Intelligence",
  description: "Data-driven analysis of drug registrations, expiry alerts, and market opportunities across 15 African markets.",
};

const CATEGORY_LABELS: Record<string, string> = {
  "expiry-watch": "Expiry Watch",
  "new-registrations": "New Registrations",
  "generic-opportunities": "Generic Opportunities",
  "market-entry": "Market Entry Intelligence",
};

const CATEGORY_COLORS: Record<string, string> = {
  "expiry-watch": "bg-red-100 text-red-700",
  "new-registrations": "bg-green-100 text-green-700",
  "generic-opportunities": "bg-blue-100 text-blue-700",
  "market-entry": "bg-purple-100 text-purple-700",
};

type Post = {
  slug: string;
  title: string;
  description: string;
  category: string;
  country_code: string | null;
  published_at: string;
};

async function getPosts(): Promise<Post[]> {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return [];
  const sql = neon(dbUrl);
  const rows = await sql`
    SELECT slug, title, description, category, country_code, published_at
    FROM blog_posts ORDER BY published_at DESC LIMIT 50
  `;
  return rows as unknown as Post[];
}

export default async function BlogPage() {
  const posts = await getPosts();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <Link href="/" className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors">AfriReg</Link>
            <p className="text-xs text-gray-500">African Pharmaceutical Regulatory Intelligence</p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/blog" className="text-sm font-medium text-blue-600">Blog</Link>
            <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">Sign in</Link>
            <Link href="/signup" className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">Sign up free</Link>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-gray-900">Regulatory Intelligence Blog</h1>
          <p className="text-gray-500 mt-2">Data-driven analysis generated weekly from 95,000+ drug registrations across 15 African markets.</p>
        </div>

        {posts.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <p>No posts yet. Check back soon.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {posts.map(post => (
              <article key={post.slug} className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
                <div className="flex items-center gap-2 mb-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${CATEGORY_COLORS[post.category] || "bg-gray-100 text-gray-600"}`}>
                    {CATEGORY_LABELS[post.category] || post.category}
                  </span>
                  <span className="text-xs text-gray-400">
                    {new Date(post.published_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
                  </span>
                </div>
                <Link href={`/blog/${post.slug}`} className="block group">
                  <h2 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors mb-2">{post.title}</h2>
                  <p className="text-sm text-gray-500 leading-relaxed">{post.description}</p>
                </Link>
                <div className="mt-4">
                  <Link href={`/blog/${post.slug}`} className="text-sm text-blue-600 hover:underline font-medium">
                    Read analysis →
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}

        <div className="mt-16 bg-blue-50 border border-blue-100 rounded-xl p-8 text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Get alerts before registrations expire</h2>
          <p className="text-gray-500 mb-6 text-sm">AfriReg Pro monitors your portfolio across all 15 markets and alerts you 90 days before expiry.</p>
          <Link href="/signup" className="inline-block px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors">
            Start free — no credit card required
          </Link>
        </div>
      </div>
    </div>
  );
}
