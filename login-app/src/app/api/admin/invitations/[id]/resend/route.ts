import { NextRequest, NextResponse } from "next/server";
import { getAdminBridgeContext, internalHeaders } from "@/lib/server/admin-bridge";

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const ctx = await getAdminBridgeContext();
  if ("error" in ctx) {
    return NextResponse.json({ error: ctx.error }, { status: 401 });
  }

  const { id } = await context.params;
  const resp = await fetch(`${ctx.apiUrl}/v1/internal/invitations/${encodeURIComponent(id)}/resend`, {
    method: "POST",
    headers: internalHeaders(ctx.secret),
    body: JSON.stringify({ actor_zitadel_user_id: ctx.actorUserId }),
  }).catch(() => null);

  if (!resp) {
    return NextResponse.json({ error: "iam_unreachable" }, { status: 502 });
  }

  const data = await resp.json().catch(() => ({}));
  return NextResponse.json(data, { status: resp.status });
}
