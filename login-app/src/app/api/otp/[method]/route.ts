import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie, setSessionCookie } from "@/lib/server/session";
import { updateSession } from "@/lib/server/zitadel-client";
import { completeAuthentication } from "@/lib/server/mfa";

// One-time-code second factor over SMS or Email.
//   POST { action: "request" }      -> trigger Zitadel to send the code
//   POST { code, authRequest }      -> verify the code and complete the flow
//
// Requires an SMS provider (SMS) / SMTP (Email) configured in Zitadel; without
// them the "request" step returns an error explaining the code can't be sent.
export async function POST(request: NextRequest, ctx: { params: Promise<{ method: string }> }) {
  const { method } = await ctx.params;
  const channel = method === "sms" ? "otpSms" : "otpEmail";

  const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
  if (!session) {
    return NextResponse.json({ error: "Session expired, please sign in again" }, { status: 401 });
  }

  const { action, code, authRequest } = await request.json();

  if (action === "request") {
    const { error } = await updateSession(session.id, {
      challenges: { [channel]: { returnCode: false } },
    });
    if (error) {
      return NextResponse.json(
        { error: `Could not send the ${method === "sms" ? "SMS" : "email"} code` },
        { status: 400 }
      );
    }
    return NextResponse.json({ sent: true });
  }

  const { data, error } = await updateSession(session.id, {
    checks: { [channel]: { code } },
  });
  if (error) {
    return NextResponse.json({ error: "Invalid code" }, { status: 400 });
  }

  const updated = { ...session, token: data?.sessionToken || session.token };
  const redirectUrl = await completeAuthentication(authRequest || "", updated);

  const response = NextResponse.json({ redirectUrl });
  setSessionCookie(response, updated);
  return response;
}
