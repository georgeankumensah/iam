import { NextRequest, NextResponse } from "next/server";
import { checkUserByEmail, requestPasswordReset } from "@/lib/server/zitadel-client";

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json();
    const { data: user } = await checkUserByEmail(email || "");
    if (user) {
      await requestPasswordReset(user.userId);
    }
  } catch {
    /* silent — never reveal whether the email exists */
  }
  return NextResponse.json({ success: true });
}
