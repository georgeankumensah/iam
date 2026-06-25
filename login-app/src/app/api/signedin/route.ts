import { NextRequest, NextResponse } from "next/server";
import { djangoCompletionUrl } from "@/lib/server/mfa";
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

    return NextResponse.json({ redirectUrl: djangoCompletionUrl(authRequest) });
  } catch {
    return NextResponse.json({ redirectUrl: null });
  }
}
