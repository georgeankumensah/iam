import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getSessionAsService, createCallback } from "@/lib/server/zitadel-client";
import { parseSessionCookie } from "@/lib/server/session";

export async function POST(request: NextRequest) {
  try {
    const { authRequest } = await request.json();
    if (!authRequest) {
      return NextResponse.json({ error: "missing authRequest" }, { status: 400 });
    }

    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("zitadel-session");
    const session = parseSessionCookie(sessionCookie?.value);

    if (!session) {
      return NextResponse.json({ error: "login_required" }, { status: 401 });
    }

    const { data: activeSession, error } = await getSessionAsService(session.id);
    if (error || !activeSession?.session?.id) {
      return NextResponse.json({ error: "login_required" }, { status: 401 });
    }

    const { data: callback } = await createCallback(authRequest, session.id, session.token);
    if (!callback?.callbackUrl) {
      return NextResponse.json({ error: "callback_failed" }, { status: 500 });
    }

    return NextResponse.json({ redirectUrl: callback.callbackUrl });
  } catch {
    return NextResponse.json({ error: "login_required" }, { status: 401 });
  }
}
