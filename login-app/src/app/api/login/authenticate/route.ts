import { NextRequest, NextResponse } from "next/server";
import { createSession, createCallback } from "@/lib/server/zitadel-client";
import { createSessionCookie } from "@/lib/server/session";

export async function POST(request: NextRequest) {
  try {
    const { userId, password, authRequest } = await request.json();

    if (!userId || !password) {
      return NextResponse.json({ error: "User ID and password are required" }, { status: 400 });
    }

    const { data: session, error: sessionError } = await createSession(userId, password);
    if (sessionError || !session) {
      return NextResponse.json({ error: sessionError || "Failed to create session" }, { status: 401 });
    }

    const cookie = createSessionCookie({
      id: session.sessionId,
      token: session.sessionToken,
      userId,
    });

    let redirectUrl: string | null = null;
    if (authRequest) {
      const { data: callback, error: cbError } = await createCallback(
        authRequest,
        session.sessionId,
        session.sessionToken
      );
      if (!cbError && callback?.callbackUrl) {
        redirectUrl = callback.callbackUrl;
      }
    }

    const response = NextResponse.json({ redirectUrl });
    response.cookies.set(cookie.name, cookie.value, cookie.options as Record<string, unknown>);
    return response;
  } catch {
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
