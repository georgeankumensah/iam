"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";

const ALLOWED_ORIGINS: string[] = [
  "http://localhost:3000",
  "http://localhost:8000",
  "http://localhost:8080",
];

function isValidRedirect(url: string): boolean {
  if (url.startsWith("/")) return true;
  try {
    const parsed = new URL(url);
    return ALLOWED_ORIGINS.some((o) => parsed.origin === o);
  } catch {
    return false;
  }
}

async function validateRedirect(uri: string): Promise<boolean> {
  if (isValidRedirect(uri)) return true;
  try {
    const resp = await fetch(`/api/validate-redirect?uri=${encodeURIComponent(uri)}`);
    const data = await resp.json();
    return data?.valid === true;
  } catch {
    return false;
  }
}

function LogoutContent() {
  const searchParams = useSearchParams();
  const redirectUri = searchParams.get("redirect_uri") || "";
  const [status, setStatus] = useState("Signing out...");

  useEffect(() => {
    let cancelled = false;

    async function doLogout() {
      try {
        await fetch("/api/logout", { method: "POST" });
      } catch {
        // Ignore errors
      }

      if (redirectUri) {
        const valid = await validateRedirect(redirectUri);
        if (!cancelled && valid) {
          window.location.href = redirectUri;
          return;
        }
      }

      if (!cancelled) setStatus("You have been signed out.");
    }

    doLogout();

    return () => { cancelled = true; };
  }, [redirectUri]);

  return (
    <Card>
      <div className="text-center">
        <h1 className="text-[22px] font-bold text-black">Sign out</h1>
        <p className="mt-3 text-[15px] text-[#777]">{status}</p>
        {!redirectUri && (
          <a
            href="/login"
            className="mt-4 inline-block text-[13px] text-[#0d6efd] hover:underline"
          >
            Sign in again
          </a>
        )}
      </div>
    </Card>
  );
}

export default function LogoutPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Signing out...</div></Card>}>
      <LogoutContent />
    </Suspense>
  );
}
