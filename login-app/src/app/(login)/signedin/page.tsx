"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

function SignedInContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const [denied, setDenied] = useState(searchParams.get("error") === "access_denied");

  useEffect(() => {
    async function handleRedirect() {
      if (denied) return;
      if (!authRequest) return;
      try {
        const resp = await fetch("/api/signedin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ authRequest }),
        });
        if (resp.ok) {
          const { redirectUrl, error } = await resp.json();
          if (redirectUrl) { window.location.href = redirectUrl; return; }
          if (error === "access_denied") { setDenied(true); return; }
        }
      } catch { /* continue showing signed-in page */ }
    }
    handleRedirect();
  }, [authRequest, denied]);

  if (denied) {
    return (
      <div className="rounded-lg bg-white p-8 text-center shadow-md">
        <div className="mb-4 text-4xl">🚫</div>
        <h2 className="mb-2 text-xl font-semibold text-gray-900">No access to this application</h2>
        <p className="text-gray-500">
          You signed in, but you haven&apos;t been granted a role in this system. Ask your
          administrator to invite you.
        </p>
        <a href="/logout" className="mt-4 inline-block text-sm text-brand-600 hover:text-brand-500">
          Sign out
        </a>
      </div>
    );
  }

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
