import { NextRequest, NextResponse } from "next/server";
import { getAdminBridgeContext, internalHeaders } from "@/lib/server/admin-bridge";

export async function DELETE(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const ctx = await getAdminBridgeContext();
    if ("error" in ctx) {
      return NextResponse.json({ error: ctx.error }, { status: 401 });
    }

    const { id } = await context.params;
    const url = new URL(`${ctx.apiUrl}/v1/internal/admin-users/${encodeURIComponent(id)}`);
    url.searchParams.set("actor_zitadel_user_id", ctx.actorUserId);

    const resp = await fetch(url, {
      method: "DELETE",
      headers: internalHeaders(ctx.secret),
    }).catch(() => null);

    if (!resp) {
      return NextResponse.json({ error: "iam_unreachable" }, { status: 502 });
    }

    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "internal_error" },
      { status: 500 }
    );
  }
}
