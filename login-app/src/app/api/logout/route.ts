import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/server/session";
import { deleteSession } from "@/lib/server/zitadel-client";

export async function POST(request: NextRequest) {
  const cookieValue = request.cookies.get("zitadel-session")?.value;
  const session = parseSessionCookie(cookieValue);

  if (session?.id) {
    await deleteSession(session.id).catch(() => {});
  }

  const response = NextResponse.json({ success: true });
  response.cookies.set("zitadel-session", "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return response;
}
