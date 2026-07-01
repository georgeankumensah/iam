import { SignJWT, importPKCS8 } from "jose";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const PRIVATE_KEY_PATH = process.env.JWT_IDP_PRIVATE_KEY_PATH || join(process.cwd(), "../../jwt-keys/private.pkcs8.pem");
const ISSUER = process.env.JWT_IDP_ISSUER || "iam-login-app";
const TTL_SECONDS = Number(process.env.JWT_IDP_TTL_SECONDS) || 300;
const KEY_ID = "jwt-idp-key-v1";

let privateKey: ReturnType<typeof importPKCS8> | null = null;

async function getKey() {
  if (!privateKey) {
    const pem = readFileSync(PRIVATE_KEY_PATH, "utf-8");
    privateKey = importPKCS8(pem, "RS256");
  }
  return privateKey;
}

export async function signJwt(sub: string, extra?: Record<string, unknown>): Promise<string> {
  const key = await getKey();
  return new SignJWT({ sub, ...extra })
    .setProtectedHeader({ alg: "RS256", kid: KEY_ID })
    .setIssuer(ISSUER)
    .setAudience("zitadel")
    .setIssuedAt()
    .setExpirationTime(`${TTL_SECONDS}s`)
    .sign(await key);
}
