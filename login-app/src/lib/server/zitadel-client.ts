import "server-only";
import crypto from "node:crypto";
import http from "node:http";
import { createLogger } from "../logger";

const logger = createLogger("zitadel-client");

const ZITADEL_EXTERNAL_DOMAIN = process.env.ZITADEL_EXTERNAL_DOMAIN || "localhost:8080";

let cachedToken: { token: string; expiresAt: number } | null = null;

function jwtFromEnv(): string {
  const file = process.env.ZITADEL_SERVICE_USER_TOKEN_FILE;
  if (file) {
    const fs = require("node:fs");
    return fs.readFileSync(file, "utf8");
  }
  return process.env.ZITADEL_SERVICE_USER_TOKEN || "";
}

function b64(s: string | Buffer): string {
  return Buffer.from(s).toString("base64url");
}

function getJwtAssertion(keyData: Record<string, string>): string {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", kid: keyData.keyId };
  const payload = {
    iss: keyData.userId,
    sub: keyData.userId,
    aud: `http://${ZITADEL_EXTERNAL_DOMAIN}`,
    iat: now,
    exp: now + 3600,
  };
  const message = b64(JSON.stringify(header)) + "." + b64(JSON.stringify(payload));
  const sig = crypto.sign("RSA-SHA256", Buffer.from(message), keyData.key);
  return message + "." + b64(sig);
}

function httpRequest(
  hostname: string,
  port: number,
  method: string,
  path: string,
  body: string | undefined,
  extraHeaders: Record<string, string>
): Promise<{ status: number; body: string }> {
  return new Promise((resolve) => {
    const opts: http.RequestOptions = {
      hostname,
      port,
      path,
      method,
      headers: {
        Host: ZITADEL_EXTERNAL_DOMAIN,
        ...extraHeaders,
      },
    };
    if (body !== undefined) {
      (opts.headers as Record<string, string>)["Content-Length"] = Buffer.byteLength(body).toString();
    }
    const req = http.request(opts, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => resolve({ status: res.statusCode || 0, body: data }));
    });
    req.on("error", (e) => resolve({ status: 0, body: e.message }));
    if (body !== undefined) req.write(body);
    req.end();
  });
}

function getApiHost(): { hostname: string; port: number } {
  const url = process.env.ZITADEL_API_URL || "http://zitadel:8080";
  const parsed = new URL(url);
  return { hostname: parsed.hostname, port: Number(parsed.port) || 8080 };
}

async function getAccessToken(): Promise<string> {
  if (cachedToken && Date.now() < cachedToken.expiresAt) {
    return cachedToken.token;
  }

  const raw = jwtFromEnv();
  if (!raw) {
    throw new Error("ZITADEL_SERVICE_USER_TOKEN or ZITADEL_SERVICE_USER_TOKEN_FILE not set");
  }

  let keyData: Record<string, string>;
  try {
    keyData = JSON.parse(raw) as Record<string, string>;
  } catch {
    cachedToken = { token: raw, expiresAt: Date.now() + 3600_000 };
    return raw;
  }

  const assertion = getJwtAssertion(keyData);
  const form =
    "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" +
    "&assertion=" + encodeURIComponent(assertion) +
    "&scope=openid%20profile%20urn:zitadel:iam:org:project:id:zitadel:aud";

  const { hostname, port } = getApiHost();
  const { status, body } = await httpRequest(
    hostname,
    port,
    "POST",
    "/oauth/v2/token",
    form,
    { "Content-Type": "application/x-www-form-urlencoded" }
  );

  if (status !== 200) {
    throw new Error(`Token exchange failed: ${status} ${body}`);
  }

  const data = JSON.parse(body) as { access_token: string; expires_in?: number };
  const expiresIn = (data.expires_in || 3600) * 1000;
  cachedToken = {
    token: data.access_token,
    expiresAt: Date.now() + expiresIn - 60_000,
  };
  return data.access_token;
}

export async function fetchFromZitadel<T>(
  path: string,
  options: { method?: string; body?: string; headers?: Record<string, string> } = {}
): Promise<{ data: T | null; error: string | null }> {
  try {
    const token = await getAccessToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    };

    const { hostname, port } = getApiHost();
    const { status, body: respBody } = await httpRequest(
      hostname,
      port,
      (options.method || "GET").toUpperCase(),
      path,
      options.body,
      headers
    );

    if (status < 200 || status >= 300) {
      logger.error("Zitadel API error", { path, status, body: respBody });
      return { data: null, error: `Zitadel API error: ${status} ${respBody}` };
    }

    if (status === 204 || !respBody) {
      return { data: null as T | null, error: null };
    }

    const data = JSON.parse(respBody) as T;
    return { data, error: null };
  } catch (err) {
    logger.error("Zitadel API request failed", {
      path,
      error: err instanceof Error ? err.message : String(err),
    });
    return { data: null, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function checkUserByLoginName(loginName: string) {
  const result = await fetchFromZitadel<{
    result: Array<{ id: string; userName: string; preferredLoginName: string }>;
  }>("/management/v1/users/_search", {
    method: "POST",
    body: JSON.stringify({
      query: { offset: "0", limit: 100, asc: true },
      queries: [
        {
          userNameQuery: {
            userName: loginName,
            method: "USER_NAME_QUERY_METHOD_EQUALS",
          },
        },
      ],
    }),
  });

  if (result.error) return { data: null, error: result.error };
  const user = result.data?.result?.[0];
  if (!user) return { data: null, error: "User not found" };
  return {
    data: { userId: user.id, displayName: user.userName },
    error: null,
  };
}

export async function checkUserByEmail(email: string) {
  const result = await fetchFromZitadel<{
    result: Array<{ id: string; userName: string }>;
  }>("/management/v1/users/_search", {
    method: "POST",
    body: JSON.stringify({
      query: { offset: "0", limit: 100, asc: true },
      queries: [
        {
          loginNameQuery: {
            loginName: email,
            method: "LOGIN_NAME_QUERY_METHOD_EQUALS",
          },
        },
      ],
    }),
  });

  if (result.error) return { data: null, error: result.error };
  const user = result.data?.result?.[0];
  if (!user) return { data: null, error: "User not found" };
  return {
    data: { userId: user.id, displayName: user.userName },
    error: null,
  };
}

export async function requestPasswordReset(userId: string) {
  return fetchFromZitadel<Record<string, unknown>>(
    `/v2/users/${encodeURIComponent(userId)}/password_reset`,
    {
      method: "POST",
      body: JSON.stringify({
        notificationType: "NOTIFICATION_TYPE_PASSWORD_RESET",
        returnMedium: { email: {} },
      }),
    }
  );
}

export async function createSession(userId: string) {
  return fetchFromZitadel<{ sessionId: string; sessionToken: string }>(
    "/v2/sessions",
    {
      method: "POST",
      body: JSON.stringify({
        checks: { user: { userId } },
        metadata: {},
      }),
    }
  );
}

export async function checkPassword(sessionId: string, password: string) {
  return fetchFromZitadel<{ sessionToken: string }>(
    `/v2/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({
        checks: { password: { password } },
      }),
    }
  );
}

export async function getSession(sessionId: string, sessionToken: string) {
  return fetchFromZitadel<{
    id: string;
    factors: { authenticationLevel?: number; mfaLevel?: number };
  }>(`/v2/sessions/${sessionId}`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  });
}

// Progressively updates a session with checks (verify a factor) and/or
// challenges (request a factor). Uses the service-user token (the login client),
// which is authorised for session writes. Returns the rotated sessionToken and
// any challenge payloads (e.g. WebAuthn options, sent OTP codes).
export async function updateSession(sessionId: string, body: Record<string, unknown>) {
  return fetchFromZitadel<{
    sessionToken: string;
    challenges?: {
      webAuthN?: { publicKeyCredentialRequestOptions?: unknown };
      otpSms?: unknown;
      otpEmail?: unknown;
    };
  }>(`/v2/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function getLoginSettings() {
  return fetchFromZitadel<{
    settings: { forceMfa?: boolean; forceMfaLocalOnly?: boolean };
  }>("/v2/settings/login");
}

// Lists the authentication methods a user has configured (TOTP, OTP-SMS,
// OTP-EMAIL, U2F, PASSKEY). Used to decide MFA challenge vs. enrollment.
export async function listUserAuthMethods(userId: string) {
  return fetchFromZitadel<{ authMethodTypes?: string[] }>(
    `/v2/users/${encodeURIComponent(userId)}/authentication_methods`
  );
}

// ---- Enrollment ----------------------------------------------------------

export async function startTotpRegistration(userId: string) {
  return fetchFromZitadel<{ uri: string; secret: string }>(
    `/v2/users/${encodeURIComponent(userId)}/totp`,
    { method: "POST", body: JSON.stringify({}) }
  );
}

export async function verifyTotpRegistration(userId: string, code: string) {
  return fetchFromZitadel<Record<string, unknown>>(
    `/v2/users/${encodeURIComponent(userId)}/totp/verify`,
    { method: "POST", body: JSON.stringify({ code }) }
  );
}

export async function startPasskeyRegistration(userId: string, domain: string) {
  return fetchFromZitadel<{
    passkeyId: string;
    publicKeyCredentialCreationOptions: unknown;
  }>(`/v2/users/${encodeURIComponent(userId)}/passkeys`, {
    method: "POST",
    body: JSON.stringify({
      authenticator: "PASSKEY_AUTHENTICATOR_UNSPECIFIED",
      domain,
    }),
  });
}

export async function verifyPasskeyRegistration(
  userId: string,
  passkeyId: string,
  publicKeyCredential: unknown,
  passkeyName: string
) {
  return fetchFromZitadel<Record<string, unknown>>(
    `/v2/users/${encodeURIComponent(userId)}/passkeys/${encodeURIComponent(passkeyId)}`,
    { method: "POST", body: JSON.stringify({ publicKeyCredential, passkeyName }) }
  );
}

export async function getAuthRequest(authRequestId: string) {
  const result = await fetchFromZitadel<{
    authRequest: {
      id: string;
      clientId: string;
      redirectUri: string;
      scope: string[];
      hintUserId?: string;
      loginHint?: string;
      prompt?: string[];
      uiLocales?: string[];
    };
  }>(`/v2/oidc/auth_requests/${authRequestId}`);

  if (result.error || !result.data?.authRequest) {
    return { data: null, error: result.error || "Auth request not found" };
  }

  const ar = result.data.authRequest;
  return {
    data: {
      id: ar.id,
      clientId: ar.clientId,
      redirectUri: ar.redirectUri,
      scope: ar.scope,
      hintUserId: ar.hintUserId,
      loginHint: ar.loginHint,
      prompt: ar.prompt,
      uiLocales: ar.uiLocales,
    },
    error: null,
  };
}

export async function createCallback(authRequestId: string, sessionId: string, sessionToken: string) {
  return fetchFromZitadel<{ callbackUrl: string }>(
    `/v2/oidc/auth_requests/${encodeURIComponent(authRequestId)}`,
    {
      method: "POST",
      body: JSON.stringify({
        session: { sessionId, sessionToken },
      }),
    }
  );
}

export async function deleteSession(sessionId: string) {
  return fetchFromZitadel<null>(`/v2/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
}

// Reads a session using the service-user token (not the session token, which
// Zitadel rejects for this endpoint with 403 AUTHZ-Kl3p0). Used to verify a
// session is still alive and check its authentication level.
export async function getSessionAsService(sessionId: string) {
  return fetchFromZitadel<{
    session: {
      id: string;
      factors?: {
        user?: { id: string };
        password?: { verifiedAt?: string };
        webAuthN?: { verifiedAt?: string };
        totp?: { verifiedAt?: string };
        otpSms?: { verifiedAt?: string };
        otpEmail?: { verifiedAt?: string };
      };
    };
  }>(`/v2/sessions/${encodeURIComponent(sessionId)}`);
}

// Returns true if the session has satisfied MFA (any second factor verified).
export function sessionHasMfa(factors: {
  webAuthN?: { verifiedAt?: string };
  totp?: { verifiedAt?: string };
  otpSms?: { verifiedAt?: string };
  otpEmail?: { verifiedAt?: string };
}): boolean {
  return !!(factors.webAuthN?.verifiedAt || factors.totp?.verifiedAt || factors.otpSms?.verifiedAt || factors.otpEmail?.verifiedAt);
}

export async function listUserSessions(userId: string) {
  return fetchFromZitadel<{ sessions: Array<{ id: string }> }>("/v2/sessions/search", {
    method: "POST",
    body: JSON.stringify({
      queries: [{ userIdQuery: { id: userId } }],
    }),
  });
}
