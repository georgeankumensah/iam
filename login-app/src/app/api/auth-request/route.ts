import { NextRequest, NextResponse } from "next/server";
import { getAuthRequest } from "@/lib/server/zitadel-client";

export async function GET(request: NextRequest) {
  const id = request.nextUrl.searchParams.get("id");
  if (!id) {
    return NextResponse.json({ error: "missing id" }, { status: 400 });
  }

  const { data, error } = await getAuthRequest(id);
  if (error || !data) {
    return NextResponse.json({ error: error || "not_found" }, { status: 404 });
  }

  return NextResponse.json({
    id: data.id,
    clientId: data.clientId,
    redirectUri: data.redirectUri,
    scope: data.scope,
    prompt: data.prompt || [],
  });
}
