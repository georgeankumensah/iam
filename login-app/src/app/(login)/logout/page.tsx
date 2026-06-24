"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";

function LogoutContent() {
  const searchParams = useSearchParams();
  const redirectUri = searchParams.get("redirect_uri") || "";
  const [status, setStatus] = useState("Signing out...");

  useEffect(() => {
    async function doLogout() {
      try {
        await fetch("/api/logout", { method: "POST" });
      } catch {
        // Ignore errors
      }

      if (redirectUri) {
        window.location.href = redirectUri;
        return;
      }

      setStatus("You have been signed out.");
    }

    doLogout();
  }, [redirectUri]);

  return (
    <Card>
      <div className="text-center">
        <h2 className="mb-2 text-xl font-semibold text-gray-900">Sign out</h2>
        <p className="text-gray-500">{status}</p>
        {!redirectUri && (
          <a
            href="/login"
            className="mt-4 inline-block text-sm text-brand-600 hover:text-brand-500"
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
