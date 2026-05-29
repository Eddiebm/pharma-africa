import { SignJWT, jwtVerify } from "jose";

function getKey(): Uint8Array {
  const s = process.env.JWT_SECRET;
  if (!s) throw new Error("JWT_SECRET is not set");
  return new TextEncoder().encode(s);
}

export interface SessionUser {
  id: string;
  email: string;
  company_name: string | null;
  plan: "free" | "pro" | "enterprise";
}

export async function hashPassword(password: string): Promise<string> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const km = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations: 100_000 }, km, 256);
  const hex = (a: Uint8Array) => Array.from(a).map(b => b.toString(16).padStart(2, "0")).join("");
  return `${hex(salt)}:${hex(new Uint8Array(bits))}`;
}

export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  const [saltHex, storedHex] = stored.split(":");
  if (!saltHex || !storedHex) return false;
  const salt = new Uint8Array(saltHex.match(/.{2}/g)!.map(b => parseInt(b, 16)));
  const km = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations: 100_000 }, km, 256);
  const candidateHex = Array.from(new Uint8Array(bits)).map(b => b.toString(16).padStart(2, "0")).join("");
  if (candidateHex.length !== storedHex.length) return false;
  let diff = 0;
  for (let i = 0; i < candidateHex.length; i++) diff |= candidateHex.charCodeAt(i) ^ storedHex.charCodeAt(i);
  return diff === 0;
}

export async function createToken(user: SessionUser): Promise<string> {
  return new SignJWT({ id: user.id, email: user.email, company_name: user.company_name, plan: user.plan })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("7d")
    .setIssuedAt()
    .sign(getKey());
}

export async function verifyToken(req: Request): Promise<SessionUser | null> {
  const cookie = req.headers.get("cookie") || "";
  const match = cookie.match(/app_session=([^;]+)/);
  if (!match) return null;
  try {
    const { payload } = await jwtVerify(match[1], getKey());
    return payload as unknown as SessionUser;
  } catch {
    return null;
  }
}

// No Secure flag — add it when HTTPS is configured
export const sessionCookieSet = (token: string) =>
  `app_session=${token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${7 * 24 * 3600}`;

export const sessionCookieClear = () =>
  `app_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0`;
