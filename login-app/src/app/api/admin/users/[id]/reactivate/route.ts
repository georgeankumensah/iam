import { NextRequest, NextResponse } from "next/server";
import { getAdminBridgeContext, internalHeaders } from "@/lib/server/admin-bridge";

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const ctx = await getAdminBridgeContext();
    if ("error" in ctx) {
      return NextResponse.json({ error: ctx.error }, { status: 401 });
    }

    const { id } = await context.params;
    const apiBase = ctx.apiUrl.replace(/\/+$/, "");
    const url = `${apiBase}/v1/internal/admin-users/${encodeURIComponent(id)}/reactivate`;

    const resp = await fetch(url, {
      method: "POST",
      headers: internalHeaders(ctx.secret),
    });

    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "internal_error";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}