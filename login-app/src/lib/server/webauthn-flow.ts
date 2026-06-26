import "server-only";
import { NextRequest, NextResponse } from "next/server";
import { updateSession } from "./zitadel-client";
import { completeAuthentication } from "./mfa";
import { parseSessionCookie, setSessionCookie } from "./session";

function rpDomain(request: NextRequest): string {
  // The WebAuthn RP ID is the host without the port (e.g. "localhost").
  return (request.headers.get("host") || "localhost:3000").split(":")[0];
}

// Requests a WebAuthn assertion challenge and returns the
// publicKeyCredentialRequestOptions for navigator.credentials.get().
// userVerification distinguishes passkey (REQUIRED) from U2F security keys
// (DISCOURAGED).
export async function webauthnChallenge(
  request: NextRequest,
  userVerification: string
): Promise<NextResponse> {
  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
  if (!session) {
    return NextResponse.json({ error: "Session expired, please sign in again" }, { status: 401 });
  }

  const { data, error } = await updateSession(session.id, {
    challenges: {
      webAuthN: { domain: rpDomain(request), userVerificationRequirement: userVerification },
    },
  });
  if (error) {
    return NextResponse.json({ error: "Could not start security key verification" }, { status: 400 });
  }

  const options = data?.challenges?.webAuthN?.publicKeyCredentialRequestOptions ?? {};
  const response = NextResponse.json(options);
  if (data?.sessionToken) setSessionCookie(response, { ...session, token: data.sessionToken });
  return response;
}

// Verifies a WebAuthn assertion against the session and completes the flow.
// Shared by the passkey and U2F challenge pages.
export async function webauthnVerify(request: NextRequest): Promise<NextResponse> {
  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
  if (!session) {
    return NextResponse.json({ error: "Session expired, please sign in again" }, { status: 401 });
  }

  let assertion: unknown, authRequest: string;
  try {
    ({ assertion, authRequest = "" } = await request.json());
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }
  if (!assertion) {
    return NextResponse.json({ error: "Missing assertion" }, { status: 400 });
  }
  const { data, error } = await updateSession(session.id, {
    checks: { webAuthN: { credentialAssertionData: assertion } },
  });
  if (error) {
    return NextResponse.json({ error: "Security key verification failed" }, { status: 400 });
  }

  const updated = { ...session, token: data?.sessionToken || session.token };
  const redirectUrl = await completeAuthentication(authRequest || "", updated);

  const response = NextResponse.json({ redirectUrl });
  setSessionCookie(response, updated);
  return response;
}
