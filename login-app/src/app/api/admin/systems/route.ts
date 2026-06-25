import { NextResponse } from "next/server";
import { getAdminBridgeContext, internalHeaders } from "@/lib/server/admin-bridge";

export async function GET() {
  const ctx = await getAdminBridgeContext();
  if ("error" in ctx) {
    return NextResponse.json({ error: ctx.error }, { status: 401 });
  }

  const url = new URL(`${ctx.apiUrl}/v1/internal/admin-systems`);
  url.searchParams.set("actor_zitadel_user_id", ctx.actorUserId);

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
