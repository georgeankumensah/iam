import { NextResponse } from "next/server";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createPublicKey } from "node:crypto";

const PUBLIC_KEY_PATH = process.env.JWT_IDP_PUBLIC_KEY_PATH || join(process.cwd(), "../../jwt-keys/public.pem");

export async function GET() {
  try {
    const pem = readFileSync(PUBLIC_KEY_PATH, "utf-8");
    const pubKey = createPublicKey(pem);
    const jwk = pubKey.export({ format: "jwk" }) as Record<string, string>;
    jwk.alg = "RS256";
    jwk.kid = "jwt-idp-key-v1";
    jwk.use = "sig";
    return NextResponse.json(
      { keys: [jwk] },
      { headers: { "Content-Type": "application/jwk-set+json" } },
    );
  } catch {
    return NextResponse.json({ error: "keys not available" }, { status: 500 });
  }
}
