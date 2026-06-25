import { NextRequest, NextResponse } from "next/server";
import { createCallback } from "@/lib/server/zitadel-client";
import { parseSessionCookie } from "@/lib/server/session";

export async function POST(request: NextRequest) {
  try {
    const { authRequest } = await request.json();
    if (!authRequest) {
      return NextResponse.json({ redirectUrl: null });
    }

    const session = parseSessionCookie(request.cookies.get("zitadel-session")?.value);
    if (!session) {
      return NextResponse.json({ redirectUrl: null });
    }

    const { data: callback, error } = await createCallback(authRequest, session.id, session.token);
    if (callback?.callbackUrl) {
      return NextResponse.json({ redirectUrl: callback.callbackUrl });
    }

    // The user authenticated but is not authorised for this application (no role
    // grant on its project — projectRoleCheck). Surface it instead of hanging.
    if (error && error.includes("GrantRequired")) {
      return NextResponse.json({ redirectUrl: null, error: "access_denied" });
    }

    return NextResponse.json({ redirectUrl: null });
  } catch {
    return NextResponse.json({ redirectUrl: null });
  }
}
