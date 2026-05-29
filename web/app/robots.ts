import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/blog"],
        disallow: ["/api/", "/dashboard", "/search", "/portfolio", "/alerts", "/billing"],
      },
    ],
    sitemap: "https://africaregulatory.com/sitemap.xml",
  };
}
