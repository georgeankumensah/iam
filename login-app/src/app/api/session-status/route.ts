import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/server/session";
import { getSessionAsService } from "@/lib/server/zitadel-client";

// Client SPAs (different ports, same site "localhost") poll this endpoint to
// learn whether the shared Zitadel SSO session is still alive. When the user
// logs out of any app, the session is terminated server-side and the shared
// cookie is cleared, so this returns { authenticated: false } and the other
// apps sign themselves out. Origins must be explicitly allow-listed because
// the request is credentialed (cannot use "*").
const ALLOWED_ORIGINS = new Set(
  (process.env.ALLOWED_CORS_ORIGINS || "http://localhost:5173,http://localhost:5174").split(",")
);

function corsHeaders(origin: string | null): Record<string, string> {
  const headers: Record<string, string> = { "Cache-Control": "no-store" };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Credentials"] = "true";
    headers["Vary"] = "Origin";
  }
  return headers;
}

export async function OPTIONS(request: NextRequest) {
  const origin = request.headers.get("origin");
  return new NextResponse(null, {
    status: 204,
    headers: {
      ...corsHeaders(origin),
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}

export async function GET(request: NextRequest) {
  const origin = request.headers.get("origin");
  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);

  let authenticated = false;
  let userId: string | undefined;

  // Presence of the cookie is not enough: another device/app may have
  // terminated this user's sessions while this browser still holds the cookie.
  // Verify the session still exists server-side so cross-device logout works.
  if (session?.id) {
    const { data, error } = await getSessionAsService(session.id);
    const sess = data?.session;
    const belongsToUser = !session.userId || sess?.factors?.user?.id === session.userId;
    if (!error && sess?.id && belongsToUser) {
      authenticated = true;
      userId = session.userId;
    }
  }

  return NextResponse.json({ authenticated, userId }, { headers: corsHeaders(origin) });
}
