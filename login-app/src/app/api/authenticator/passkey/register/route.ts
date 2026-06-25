import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/server/session";
import { startPasskeyRegistration } from "@/lib/server/zitadel-client";

// Begins passkey enrollment, returning the creation options for
// navigator.credentials.create() plus the passkeyId needed to verify.
export async function POST(request: NextRequest) {
  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
  if (!session) {
    return NextResponse.json({ error: "Session expired, please sign in again" }, { status: 401 });
  }

  const domain = (request.headers.get("host") || "localhost:3000").split(":")[0];
  const { data, error } = await startPasskeyRegistration(session.userId, domain);
  if (error || !data) {
    return NextResponse.json({ error: "Could not start passkey setup" }, { status: 400 });
  }

  return NextResponse.json({
    passkeyId: data.passkeyId,
    publicKey: data.publicKeyCredentialCreationOptions,
  });
}
