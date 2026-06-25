import { NextRequest, NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/server/session";
import { deleteSession, listUserSessions } from "@/lib/server/zitadel-client";

export async function POST(request: NextRequest) {
  const cookieValue = request.cookies.get("zitadel-session")?.value;
  const session = parseSessionCookie(cookieValue);

  if (session?.userId) {
    // Single Logout: terminate every Zitadel session that belongs to this
    // user — across all client apps and devices — not just the current one.
    // This is what makes a logout from one app (e.g. AMS) sign the user out
    // of the others (e.g. NBES), whose SPAs detect the dead session via the
    // /api/session-status endpoint and clear their local tokens.
    const { data } = await listUserSessions(session.userId);
    const ids = new Set(data?.sessions?.map((s) => s.id) ?? []);
    if (session.id) ids.add(session.id);
    await Promise.all([...ids].map((id) => deleteSession(id).catch(() => {})));
  } else if (session?.id) {
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
