import { NextRequest, NextResponse } from "next/server";
import { checkUserByLoginName } from "@/lib/server/zitadel-client";

export async function POST(request: NextRequest) {
  try {
    const { loginName } = await request.json();
    if (!loginName) {
      return NextResponse.json({ error: "Login name is required" }, { status: 400 });
    }

    const { data: user, error } = await checkUserByLoginName(loginName);
    if (error || !user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    return NextResponse.json({ userId: user.userId });
  } catch {
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
