import { NextRequest } from "next/server";
import { webauthnVerify } from "@/lib/server/webauthn-flow";

export async function POST(request: NextRequest) {
  return webauthnVerify(request);
}
