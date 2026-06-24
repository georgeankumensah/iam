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

    const { data: callback } = await createCallback(authRequest, session.id);
    if (callback?.callbackUrl) {
      return NextResponse.json({ redirectUrl: callback.callbackUrl });
    }

    return NextResponse.json({ redirectUrl: null });
  } catch {
    return NextResponse.json({ redirectUrl: null });
  }
}
