import "server-only";
import { cookies } from "next/headers";
import { getSessionAsService } from "./zitadel-client";
import { parseSessionCookie } from "./session";

export async function getAdminBridgeContext() {
  const cookieStore = await cookies();
  const session = parseSessionCookie(cookieStore.get("zitadel-session")?.value);
  if (!session?.id || !session.userId) {
    return { error: "not_authenticated" as const };
  }

  const { data, error } = await getSessionAsService(session.id);
  if (error || !data?.session?.id) {
    return { error: "session_expired" as const };
  }

  return {
    apiUrl: process.env.IAM_API_URL || "http://django:8000",
    secret: process.env.ONBOARDING_INTERNAL_SECRET || "",
    actorUserId: session.userId,
  };
}

export function internalHeaders(secret: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Internal-Secret": secret,
  };
}
