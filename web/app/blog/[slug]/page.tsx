export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

const CATEGORY_LABELS: Record<string, string> = {
  "expiry-watch": "Expiry Watch",
  "new-registrations": "New Registrations",
  "generic-opportunities": "Generic Opportunities",
  "market-entry": "Market Entry Intelligence",
};

type Post = {
  slug: string;
  title: string;
  description: string;
  content: string;
  category: string;
  country_code: string | null;
  published_at: string;
};

async function getPost(slug: string): Promise<Post | null> {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return null;
  const sql = neon(dbUrl);
  const rows = await sql`
    SELECT slug, title, description, content, category, country_code, published_at
    FROM blog_posts WHERE slug = ${slug}
  `;
  return (rows[0] as Post) || null;
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) return { title: "Not Found — AfriReg" };
  return {
    title: `${post.title} — AfriReg`,
    description: post.description,
    openGraph: {
      title: post.title,
      description: post.description,
      type: "article",
      publishedTime: post.published_at,
      siteName: "AfriReg",
    },
  };
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) notFound();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.description,
    datePublished: post.published_at,
    publisher: {
      "@type": "Organization",
      name: "AfriReg",
      url: "https://africaregulatory.com",
    },
    about: {
      "@type": "Thing",
      name: "African Pharmaceutical Regulation",
    },
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <Link href="/" className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors">AfriReg</Link>
            <p className="text-xs text-gray-500">African Pharmaceutical Regulatory Intelligence</p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/blog" className="text-sm text-gray-600 hover:text-gray-900">Blog</Link>
            <Link href="/reports" className="text-sm text-gray-600 hover:text-gray-900">Reports</Link>
            <Link href="/pricing" className="text-sm text-gray-600 hover:text-gray-900">Pricing</Link>
            <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">Sign in</Link>
            <Link href="/signup" className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">Sign up free</Link>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="mb-2">
          <Link href="/blog" className="text-sm text-gray-400 hover:text-gray-600">← All posts</Link>
        </div>

        <article>
          <div className="flex items-center gap-3 mt-6 mb-4">
            <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
              {CATEGORY_LABELS[post.category] || post.category}
            </span>
            <time className="text-xs text-gray-400" dateTime={post.published_at}>
              {new Date(post.published_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
            </time>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-4 leading-tight">{post.title}</h1>
          <p className="text-lg text-gray-500 mb-8 leading-relaxed">{post.description}</p>

          <div
            className="prose prose-gray max-w-none"
            dangerouslySetInnerHTML={{ __html: post.content }}
          />
        </article>

        <div className="mt-16 bg-blue-50 border border-blue-100 rounded-xl p-8 text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Track registrations before they expire</h2>
          <p className="text-gray-500 mb-6 text-sm">AfriReg Pro monitors your portfolio across all 15 markets and sends weekly intelligence digests — automatically.</p>
          <Link href="/signup" className="inline-block px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors">
            Start free — no credit card required
          </Link>
        </div>
      </div>
    </div>
  );
}
