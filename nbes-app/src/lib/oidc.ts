const CLIENT_ID = "378872306950275078";
const REDIRECT_URI = "http://localhost:5174/login/callback";
const ZITADEL_AUTHORIZE_URL = "http://localhost:3000/oauth/v2/authorize";
const ZITADEL_TOKEN_URL = "http://localhost:3000/oauth/v2/token";
const ZITADEL_USERINFO_URL = "http://localhost:3000/oidc/v1/userinfo";
const SCOPES = "openid profile email";

function generateState(): string {
  const arr = new Uint8Array(32);
  crypto.getRandomValues(arr);
  return btoa(String.fromCharCode(...arr)).replace(/[+/=]/g, "");
}

function generateCodeVerifier(): string {
  const arr = new Uint8Array(64);
  crypto.getRandomValues(arr);
  return btoa(String.fromCharCode(...arr))
    .replace(/[+/=]/g, "")
    .substring(0, 128);
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const enc = new TextEncoder().encode(verifier);
  const hash = await crypto.subtle.digest("SHA-256", enc);
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

export function redirectToLogin() {
  buildAuthorizeUrl().then((url) => {
    window.location.href = url;
  });
}

export function silentLogin() {
  buildAuthorizeUrl("none").then((url) => {
    window.location.href = url;
  });
}

async function buildAuthorizeUrl(prompt?: string): Promise<string> {
  const state = generateState();
  const verifier = generateCodeVerifier();
  sessionStorage.setItem("oidc_state", state);
  sessionStorage.setItem("oidc_verifier", verifier);

  const challenge = await generateCodeChallenge(verifier);
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    scope: SCOPES,
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  if (prompt) params.set("prompt", prompt);
  return `${ZITADEL_AUTHORIZE_URL}?${params}`;
}

export function logout() {
  localStorage.removeItem("nbes_token_data");
  const origin = window.location.origin;
  window.location.href = `http://localhost:3000/logout?redirect_uri=${encodeURIComponent(origin + "/login?silent=false")}`;
}

const SESSION_STATUS_URL = "http://localhost:3000/api/session-status";

async function isCentralSessionAlive(): Promise<boolean | null> {
  try {
    const res = await fetch(SESSION_STATUS_URL, { credentials: "include" });
    if (!res.ok) return null;
    const data = (await res.json()) as { authenticated?: boolean };
    return Boolean(data.authenticated);
  } catch {
    return null; // transient/network error — do not force a logout
  }
}

let monitorStarted = false;

// Detect a Single Logout triggered from another app (or device): if we hold a
// local token but the shared Zitadel session is gone, drop the token and show
// the login screen. Checked on focus, on tab visibility, and on an interval.
export function startSessionMonitor() {
  if (monitorStarted) return;
  monitorStarted = true;

  const check = async () => {
    if (!getStoredToken()) return;
    const alive = await isCentralSessionAlive();
    if (alive === false) {
      localStorage.removeItem("nbes_token_data");
      window.location.href = "/login?silent=false";
    }
  };

  window.addEventListener("focus", check);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") check();
  });
  window.setInterval(check, 15000);
  void check();
}

interface TokenData {
  access_token: string;
  id_token: string;
  refresh_token?: string;
}

export function getStoredToken(): TokenData | null {
  const raw = localStorage.getItem("nbes_token_data");
  if (!raw) return null;
  return JSON.parse(raw) as TokenData;
}

export function storeToken(data: TokenData) {
  localStorage.setItem("nbes_token_data", JSON.stringify(data));
}

export async function exchangeCode(code: string, state: string, storedState: string, verifier: string): Promise<TokenData> {
  if (state !== storedState) {
    throw new Error("State mismatch — possible CSRF attack");
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
    client_id: CLIENT_ID,
    code_verifier: verifier,
  });

  const res = await fetch(ZITADEL_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Token exchange failed: ${res.status} ${err}`);
  }

  return res.json() as Promise<TokenData>;
}

export async function fetchUserinfo(accessToken: string) {
  const res = await fetch(ZITADEL_USERINFO_URL, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error("Userinfo request failed");
  return res.json();
}
