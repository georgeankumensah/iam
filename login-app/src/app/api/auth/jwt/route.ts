import { NextRequest, NextResponse } from "next/server";
import { signJwt } from "@/lib/server/jwt-signer";

const KEYCLOAK_TOKEN_URL = process.env.KEYCLOAK_TOKEN_URL || "http://keycloak:8080/realms/clet-iam/protocol/openid-connect/token";
const KEYCLOAK_CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || "iam-login-app";
const KEYCLOAK_CLIENT_SECRET = process.env.KEYCLOAK_CLIENT_SECRET || "login-app-dev-secret";
const ZITADEL_API_URL = process.env.ZITADEL_API_URL || "http://zitadel:8080";

export async function GET(request: NextRequest) {
  const authRequest = request.nextUrl.searchParams.get("authRequest") || "";
  const redirectUri = request.nextUrl.searchParams.get("redirect_uri") || "";
  const state = request.nextUrl.searchParams.get("state") || "";
  const params = new URLSearchParams();
  if (authRequest) params.set("authRequest", authRequest);
  if (redirectUri) params.set("redirect_uri", redirectUri);
  if (state) params.set("state", state);
  const qs = params.toString();
  return NextResponse.redirect(new URL(`/keycloak/login${qs ? `?${qs}` : ""}`, request.url));
}

export async function POST(request: NextRequest) {
  try {
    const { username, password, authRequest, redirectUri, state } = await request.json();

    if (!username || !password) {
      return NextResponse.json({ error: "Username and password are required" }, { status: 400 });
    }

    const tokenResp = await fetch(KEYCLOAK_TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: KEYCLOAK_CLIENT_ID,
        client_secret: KEYCLOAK_CLIENT_SECRET,
        grant_type: "password",
        username,
        password,
        scope: "openid profile email",
      }),
      signal: AbortSignal.timeout(10000),
    });

    if (!tokenResp.ok) {
      const body = await tokenResp.text();
      console.error(`[jwt-auth] Keycloak auth failed (${tokenResp.status}): ${body.slice(0, 200)}`);
      return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
    }

    const keycloakData = await tokenResp.json();
    const sub = keycloakData.sub || keycloakData.user_id || username;

    const jwt = await signJwt(sub, { email: keycloakData.email || username });

    const zitadelUrl = new URL(`${ZITADEL_API_URL}/idps/jwt`);
    if (authRequest) zitadelUrl.searchParams.set("authRequest", authRequest);
    if (redirectUri) zitadelUrl.searchParams.set("redirect_uri", redirectUri);
    if (state) zitadelUrl.searchParams.set("state", state);

    const zitadelResp = await fetch(zitadelUrl.toString(), {
      method: "GET",
      headers: {
        "x-custom-tkn": jwt,
      },
      redirect: "manual",
      signal: AbortSignal.timeout(15000),
    });

    if (zitadelResp.status >= 300 && zitadelResp.status < 400) {
      const location = zitadelResp.headers.get("location");
      if (location) {
        return NextResponse.redirect(location);
      }
    }

    const text = await zitadelResp.text();
    console.error(`[jwt-auth] Zitadel JWT IdP error (${zitadelResp.status}): ${text.slice(0, 300)}`);
    return NextResponse.redirect(
      new URL(`/error?error=jwt_idp_failed&detail=${encodeURIComponent(text.slice(0, 200))}`, request.url),
    );
  } catch (err) {
    console.error(`[jwt-auth] unexpected error: ${err instanceof Error ? err.message : String(err)}`);
    return NextResponse.redirect(new URL("/error?error=jwt_idp_failed", request.url));
  }
}
