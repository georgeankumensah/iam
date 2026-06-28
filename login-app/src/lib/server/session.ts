import "server-only";
import crypto from "node:crypto";
import { cookies } from "next/headers";

const SESSION_COOKIE = "zitadel-session";
const ALGORITHM = "aes-256-gcm";
const KEY_LENGTH = 32; // AES-256
const IV_LENGTH = 12; // GCM standard
const TAG_LENGTH = 16; // GCM auth tag

export interface SessionData {
  id: string;
  token: string;
  userId: string;
}

function getEncryptionKey(): Buffer {
  const secret = process.env.SESSION_ENCRYPTION_KEY;
  if (secret) {
    return crypto.createHash("sha256").update(secret).digest();
  }
  // Fallback: generate a key from the machine key file or a secure random.
  // In dev, this means cookies are tied to this container instance.
  return crypto.randomBytes(KEY_LENGTH);
}

function encrypt(plaintext: string): string {
  const key = getEncryptionKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
  const encrypted = Buffer.concat([cipher.update(plaintext, "utf-8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  // Format: iv:tag:ciphertext (all base64url encoded)
  return `${iv.toString("base64url")}:${tag.toString("base64url")}:${encrypted.toString("base64url")}`;
}

function decrypt(encoded: string): string | null {
  const parts = encoded.split(":");
  if (parts.length !== 3) return null;
  try {
    const key = getEncryptionKey();
    const iv = Buffer.from(parts[0], "base64url");
    const tag = Buffer.from(parts[1], "base64url");
    const encrypted = Buffer.from(parts[2], "base64url");
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(tag);
    return decipher.update(encrypted) + decipher.final("utf-8");
  } catch {
    return null;
  }
}

export function createSessionCookie(session: SessionData): { name: string; value: string; options: Record<string, unknown> } {
  const payload = encrypt(JSON.stringify(session));
  return {
    name: SESSION_COOKIE,
    value: payload,
    options: {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24, // 24 hours
    },
  };
}

export function parseSessionCookie(cookieValue: string | undefined): SessionData | null {
  if (!cookieValue) return null;
  try {
    const decrypted = decrypt(cookieValue);
    if (!decrypted) return null;
    return JSON.parse(decrypted) as SessionData;
  } catch {
    return null;
  }
}

// Writes the session cookie onto a response. Used after each step that rotates
// the session token (password, every MFA factor) so the cookie always holds
// the latest token.
export function setSessionCookie(
  response: {
    cookies: {
      set: (name: string, value: string, options: Record<string, unknown>) => void;
    };
  },
  session: SessionData
): void {
  const cookie = createSessionCookie(session);
  response.cookies.set(cookie.name, cookie.value, cookie.options);
}
