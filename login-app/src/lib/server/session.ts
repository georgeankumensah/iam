import "server-only";
import { cookies } from "next/headers";

const SESSION_COOKIE = "zitadel-session";

interface SessionData {
  id: string;
  token: string;
  userId: string;
}

export function createSessionCookie(session: SessionData): { name: string; value: string; options: Record<string, unknown> } {
  const payload = Buffer.from(JSON.stringify(session)).toString("base64");
  return {
    name: SESSION_COOKIE,
    value: payload,
    options: {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24, // 24 hours
    },
  };
}

export function parseSessionCookie(cookieValue: string | undefined): SessionData | null {
  if (!cookieValue) return null;
  try {
    return JSON.parse(Buffer.from(cookieValue, "base64").toString("utf-8")) as SessionData;
  } catch {
    return null;
  }
}
