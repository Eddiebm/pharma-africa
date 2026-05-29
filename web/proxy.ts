import { jwtVerify } from "jose";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const cookie = req.cookies.get("app_session");

  // Redirect logged-in users away from auth pages
  if (pathname === "/login" || pathname === "/signup") {
    if (cookie?.value && await isValidToken(cookie.value)) {
      return NextResponse.redirect(new URL("/dashboard", req.url));
    }
    return NextResponse.next();
  }

  // All other protected routes require auth
  if (!cookie?.value || !(await isValidToken(cookie.value))) {
    const url = new URL("/login", req.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

async function isValidToken(token: string): Promise<boolean> {
  const secret = process.env.JWT_SECRET;
  if (!secret) throw new Error("JWT_SECRET is not set");
  try {
    await jwtVerify(token, new TextEncoder().encode(secret));
    return true;
  } catch {
    return false;
  }
}

export const config = {
  matcher: ["/dashboard/:path*", "/search/:path*", "/record/:path*", "/portfolio/:path*", "/alerts/:path*", "/billing/:path*", "/login", "/signup"],
};
