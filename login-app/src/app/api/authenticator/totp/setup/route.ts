import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/server/session";
import { startTotpRegistration } from "@/lib/server/zitadel-client";

// Begins TOTP enrollment for the in-progress user, returning the otpauth URI
// (for the QR code) and the shared secret (for manual entry).
export async function POST(request: NextRequest) {
  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
  if (!session) {
    return NextResponse.json({ error: "Session expired, please sign in again" }, { status: 401 });
  }

  const { data, error } = await startTotpRegistration(session.userId);
  if (error || !data) {
    return NextResponse.json({ error: "Could not start authenticator setup" }, { status: 400 });
  }

  return NextResponse.json({ uri: data.uri, secret: data.secret });
}
