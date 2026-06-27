export function env(name: string, fallback = ""): string {
  return import.meta.env[name] || fallback;
}

export const ZITADEL_AUTHORITY = env("VITE_ZITADEL_AUTHORITY", "http://localhost:8080");
export const OIDC_CLIENT_ID = env("VITE_OIDC_CLIENT_ID");
export const OIDC_REDIRECT_URI = env("VITE_OIDC_REDIRECT_URI", "http://localhost:3001/auth/callback");
export const OIDC_POST_LOGOUT_URI = env("VITE_OIDC_POST_LOGOUT_URI", "http://localhost:3001/logout");
export const API_BASE = env("VITE_API_BASE", "http://localhost:8000");
