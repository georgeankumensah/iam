import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/server/session";
import { verifyPasskeyRegistration } from "@/lib/server/zitadel-client";

// Completes passkey enrollment. The session's MFA requirement is then satisfied
// by the normal passkey challenge (the page redirects there afterwards).
export async function POST(request: NextRequest) {
  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
  if (!session) {
    return NextResponse.json({ error: "Session expired, please sign in again" }, { status: 401 });
  }

  let passkeyId: string, credential: unknown;
  try {
    ({ passkeyId = "", credential } = await request.json());
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }
  const { error } = await verifyPasskeyRegistration(session.userId, passkeyId, credential, "Passkey");
  if (error) {
    return NextResponse.json({ error: "Passkey registration failed" }, { status: 400 });
  }

  return NextResponse.json({ ok: true });
}
