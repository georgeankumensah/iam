import "server-only";
import { getLoginSettings, listUserAuthMethods } from "./zitadel-client";
import { createLogger } from "../logger";
import type { SessionData } from "./session";

const logger = createLogger("mfa");

const DJANGO_BASE_URL = process.env.IAM_DJANGO_BASE_URL || "http://localhost:8000";

export function djangoCompletionUrl(authRequest: string): string {
  return `${DJANGO_BASE_URL}/login/complete?authRequest=${encodeURIComponent(authRequest)}`;
}

// Maps a Zitadel authentication-method-type to the login-app route that
// challenges it. Only second-factor methods are listed (password/idp excluded).
const FACTOR_ROUTES: Record<string, { factor: string; path: (ar: string) => string }> = {
  AUTHENTICATION_METHOD_TYPE_TOTP: { factor: "totp", path: (ar) => `/mfa/totp?authRequest=${ar}` },
  AUTHENTICATION_METHOD_TYPE_U2F: { factor: "u2f", path: (ar) => `/u2f?authRequest=${ar}` },
  AUTHENTICATION_METHOD_TYPE_PASSKEY: { factor: "passkey", path: (ar) => `/passkey?authRequest=${ar}` },
  AUTHENTICATION_METHOD_TYPE_OTP_SMS: { factor: "sms", path: (ar) => `/otp/sms?authRequest=${ar}` },
  AUTHENTICATION_METHOD_TYPE_OTP_EMAIL: { factor: "email", path: (ar) => `/otp/email?authRequest=${ar}` },
};

// Preference order when a user has several factors registered.
const FACTOR_PRIORITY = [
  "AUTHENTICATION_METHOD_TYPE_PASSKEY",
  "AUTHENTICATION_METHOD_TYPE_TOTP",
  "AUTHENTICATION_METHOD_TYPE_U2F",
  "AUTHENTICATION_METHOD_TYPE_OTP_EMAIL",
  "AUTHENTICATION_METHOD_TYPE_OTP_SMS",
];

export interface NextStep {
  next: "done" | "mfa" | "enroll";
  // Available second factors and their challenge URLs (when next === "mfa").
  factors: Array<{ factor: string; path: string }>;
}

// Decides what must happen after a correct password: complete, challenge an
// existing second factor, or enrol one. With forceMfa on, "done" only occurs
// if the policy is somehow disabled.
export async function decideNextStep(userId: string, authRequest: string): Promise<NextStep> {
  const [{ data: settings, error: settingsErr }, { data: methods, error: methodsErr }] = await Promise.all([
    getLoginSettings(),
    listUserAuthMethods(userId),
  ]);

  if (settingsErr) {
    logger.error("Failed to fetch login settings", { userId, error: settingsErr });
  }
  if (methodsErr) {
    logger.error("Failed to fetch user auth methods", { userId, error: methodsErr });
  }

  const forceMfa = Boolean(settings?.settings?.forceMfa || settings?.settings?.forceMfaLocalOnly);
  const types = (methods?.authMethodTypes ?? []).filter((t) => t in FACTOR_ROUTES);

  if (types.length > 0) {
    const ordered = [...types].sort(
      (a, b) => FACTOR_PRIORITY.indexOf(a) - FACTOR_PRIORITY.indexOf(b)
    );
    return {
      next: "mfa",
      factors: ordered.map((t) => ({
        factor: FACTOR_ROUTES[t].factor,
        path: FACTOR_ROUTES[t].path(authRequest),
      })),
    };
  }

  if (forceMfa) {
    return { next: "enroll", factors: [] };
  }

  return { next: "done", factors: [] };
}

// Completes the OIDC flow for a fully-authenticated session, returning the
// callback URL that sends the browser back to the client app (or null if there
// is no auth request, e.g. a direct visit to the login app).
export async function completeAuthentication(
  authRequest: string,
  _session: SessionData
): Promise<string | null> {
  if (!authRequest) return null;
  return djangoCompletionUrl(authRequest);
}
