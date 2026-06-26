import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getSessionAsService, sessionHasMfa } from "@/lib/server/zitadel-client";
import { djangoCompletionUrl } from "@/lib/server/mfa";
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

    const factors = activeSession.session.factors || {};
    if (!sessionHasMfa(factors)) {
      return NextResponse.json({ error: "mfa_required" }, { status: 401 });
    }

    return NextResponse.json({ redirectUrl: djangoCompletionUrl(authRequest) });
  } catch {
    return NextResponse.json({ error: "login_required" }, { status: 401 });
  }
}
