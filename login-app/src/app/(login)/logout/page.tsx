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
