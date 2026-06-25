import { NextRequest } from "next/server";
import { webauthnChallenge } from "@/lib/server/webauthn-flow";

export async function POST(request: NextRequest) {
  return webauthnChallenge(request, "USER_VERIFICATION_REQUIREMENT_REQUIRED");
}
