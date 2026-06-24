import { NextRequest, NextResponse } from "next/server";
import { checkUserByEmail, createSession, createCallback } from "@/lib/server/zitadel-client";
import { createSessionCookie } from "@/lib/server/session";

const FAIL = { error: "Invalid email or password" };

export async function POST(request: NextRequest) {
  try {
    const { email, password, authRequest } = await request.json();

    const userResult = await checkUserByEmail(email || "");
    const userId = userResult.data?.userId || "0";

    const sessionResult = await createSession(userId, password || "");
    if (!sessionResult.data || !userResult.data) {
      return NextResponse.json(FAIL, { status: 401 });
    }

    const cookie = createSessionCookie({
      id: sessionResult.data.sessionId,
      token: sessionResult.data.sessionToken,
      userId,
    });

    let redirectUrl: string | null = null;
    if (authRequest) {
      const { data: callback } = await createCallback(
        authRequest,
        sessionResult.data.sessionId,
        sessionResult.data.sessionToken
      );
      if (callback?.callbackUrl) {
        redirectUrl = callback.callbackUrl;
      }
    }

    const response = NextResponse.json({ redirectUrl });
    response.cookies.set(cookie.name, cookie.value, cookie.options as Record<string, unknown>);
    return response;
  } catch {
    return NextResponse.json(FAIL, { status: 401 });
  }
}
