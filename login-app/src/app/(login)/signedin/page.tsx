"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";

function SignedInContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

  useEffect(() => {
    async function handleRedirect() {
      if (!authRequest) return;
      try {
        const resp = await fetch("/api/signedin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ authRequest }),
        });
        if (resp.ok) {
          const { redirectUrl } = await resp.json();
          if (redirectUrl) { window.location.href = redirectUrl; return; }
        }
      } catch { /* continue showing signed-in page */ }
    }
    handleRedirect();
  }, [authRequest]);

  return (
    <div className="rounded-lg bg-white p-8 text-center shadow-md">
      <div className="mb-4 text-4xl">✓</div>
      <h2 className="mb-2 text-xl font-semibold text-gray-900">Signed in successfully</h2>
      <p className="text-gray-500">You are now signed in. Redirecting...</p>
    </div>
  );
}

export default function SignedInPage() {
  return (
    <Suspense fallback={<div className="rounded-lg bg-white p-8 text-center shadow-md"><p>Loading...</p></div>}>
      <SignedInContent />
    </Suspense>
  );
}
