import { NextRequest, NextResponse } from "next/server";
import { checkPassword, checkUserByEmail, createSession } from "@/lib/server/zitadel-client";
import { setSessionCookie } from "@/lib/server/session";
import { decideNextStep, completeAuthentication } from "@/lib/server/mfa";

const FAIL = { error: "Invalid email or password" };

export async function POST(request: NextRequest) {
  try {
    const { email, password, authRequest } = await request.json();

    const userResult = await checkUserByEmail(email || "");
    if (!userResult.data) {
      return NextResponse.json(FAIL, { status: 401 });
    }
    const userId = userResult.data.userId;

    const sessionResult = await createSession(userId);
    if (!sessionResult.data) {
      return NextResponse.json(FAIL, { status: 401 });
    }
    const sessionId = sessionResult.data.sessionId;

    const passwordResult = await checkPassword(sessionId, password || "");
    if (!passwordResult.data) {
      return NextResponse.json(FAIL, { status: 401 });
    }

    const session = {
      id: sessionId,
      token: passwordResult.data.sessionToken,
      userId,
    };

    // Password verified. Decide whether MFA is required before completing.
    const step = await decideNextStep(userId, authRequest || "");

    let redirectUrl: string | null = null;
    if (step.next === "done") {
      redirectUrl = await completeAuthentication(authRequest || "", session);
    }

    // Persist the (possibly partial) session so the MFA/enrollment routes can
    // continue it; the cookie token is refreshed again after each factor.
    const response = NextResponse.json({
      next: step.next,
      factors: step.factors,
      redirectUrl,
    });
    setSessionCookie(response, session);
    return response;
  } catch {
    return NextResponse.json(FAIL, { status: 401 });
  }
}
