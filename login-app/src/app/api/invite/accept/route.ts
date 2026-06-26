import { NextRequest, NextResponse } from "next/server";

// Server-to-server bridge: an invitee sets their initial password here. We hand
// the ZITADEL user id + reset code + new password to the Django onboarding
// endpoint (authenticated by a shared secret), which sets the credential in
// ZITADEL, activates the user, and returns the target system's URL.
export async function POST(request: NextRequest) {
  const { token, code, password, firstName, lastName } = await request.json();
  if (!token || !code || !password || !firstName || !lastName) {
    return NextResponse.json({ error: "missing fields" }, { status: 400 });
  }

  const apiUrl = process.env.IAM_API_URL || "http://django:8000";
  const secret = process.env.ONBOARDING_INTERNAL_SECRET || "";

  const resp = await fetch(`${apiUrl}/v1/onboarding/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Internal-Secret": secret },
    body: JSON.stringify({ lookup_token: token, code, password, first_name: firstName, last_name: lastName }),
  }).catch(() => null);

  if (!resp || !resp.ok) {
    return NextResponse.json({ error: "Invalid or expired invitation" }, { status: 400 });
  }

  const data = await resp.json();
  return NextResponse.json({ systemUrl: data?.data?.system_url || null });
}
