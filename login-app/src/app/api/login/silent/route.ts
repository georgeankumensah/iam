import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getSession as getZitadelSession, createCallback } from "@/lib/server/zitadel-client";
import { parseSessionCookie, createSessionCookie } from "@/lib/server/session";

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

    const { data: activeSession, error } = await getZitadelSession(session.id, session.token);
    if (error || !activeSession) {
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
