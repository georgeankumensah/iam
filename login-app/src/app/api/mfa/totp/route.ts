import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie, setSessionCookie } from "@/lib/server/session";
import { updateSession } from "@/lib/server/zitadel-client";
import { completeAuthentication } from "@/lib/server/mfa";

// Verifies a TOTP code against the in-progress session, then completes the
// OIDC flow.
export async function POST(request: NextRequest) {
  let code: string, authRequest: string;
  try {
    ({ code = "", authRequest = "" } = await request.json());
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }
  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
  if (!session) {
    return NextResponse.json({ error: "Session expired, please sign in again" }, { status: 401 });
  }

  const { data, error } = await updateSession(session.id, { checks: { totp: { code } } });
  if (error) {
    return NextResponse.json({ error: "Invalid code" }, { status: 400 });
  }

  // The session token only rotates on some updates; keep the current one if not
  // returned.
  const updated = { ...session, token: data?.sessionToken || session.token };
  const redirectUrl = await completeAuthentication(authRequest || "", updated);

  const response = NextResponse.json({ redirectUrl });
  setSessionCookie(response, updated);
  return response;
}
