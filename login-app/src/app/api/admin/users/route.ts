import { NextRequest, NextResponse } from "next/server";
import { getAdminBridgeContext, internalHeaders } from "@/lib/server/admin-bridge";

export async function GET(request: NextRequest) {
  const ctx = await getAdminBridgeContext();
  if ("error" in ctx) {
    return NextResponse.json({ error: ctx.error }, { status: 401 });
  }

  const url = new URL(`${ctx.apiUrl}/v1/internal/admin-users`);
  url.searchParams.set("actor_zitadel_user_id", ctx.actorUserId);
  for (const key of ["search", "user_type", "status", "page", "page_size"]) {
    const val = request.nextUrl.searchParams.get(key);
    if (val) url.searchParams.set(key, val);
  }

  const resp = await fetch(url, {
    headers: internalHeaders(ctx.secret),
    cache: "no-store",
  }).catch(() => null);

  if (!resp) {
    return NextResponse.json({ error: "iam_unreachable" }, { status: 502 });
  }

  const data = await resp.json().catch(() => ({}));
  return NextResponse.json(data, { status: resp.status });
}
