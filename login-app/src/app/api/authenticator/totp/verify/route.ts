import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie, setSessionCookie } from "@/lib/server/session";
import { verifyTotpRegistration, updateSession } from "@/lib/server/zitadel-client";
import { completeAuthentication } from "@/lib/server/mfa";

// Completes TOTP enrollment: activates the authenticator with the user's code,
// then satisfies the session's MFA requirement. If the same code cannot be
// reused for the session check (replay protection), asks the page to send the
// user to the normal TOTP challenge for a fresh code.
export async function POST(request: NextRequest) {
  const { code, authRequest } = await request.json();
  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
  if (!session) {
    return NextResponse.json({ error: "Session expired, please sign in again" }, { status: 401 });
  }

  const reg = await verifyTotpRegistration(session.userId, code);
  if (reg.error) {
    return NextResponse.json({ error: "Invalid code" }, { status: 400 });
  }

  // Try to use the same code as the session's second-factor check.
  const upd = await updateSession(session.id, { checks: { totp: { code } } });
  if (upd.error) {
    // Code already consumed by registration — challenge with a fresh one.
    return NextResponse.json({ next: "mfa", redirectTo: `/mfa/totp?authRequest=${authRequest || ""}` });
  }

  const updated = { ...session, token: upd.data?.sessionToken || session.token };
  const redirectUrl = await completeAuthentication(authRequest || "", updated);

  const response = NextResponse.json({ redirectUrl });
  setSessionCookie(response, updated);
  return response;
}
