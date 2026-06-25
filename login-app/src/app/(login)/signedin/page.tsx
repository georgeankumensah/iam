"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Ban, Check } from "lucide-react";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

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
      <Card>
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600">
          <Ban size={22} />
        </div>
        <h1 className="text-center text-[22px] font-bold text-black">No access to this application</h1>
        <p className="mx-auto mt-3 max-w-[430px] text-center text-[15px] leading-6 text-[#777]">
          You signed in, but you haven&apos;t been granted a role in this system. Ask your
          administrator to invite you.
        </p>
        <a href="/logout" className="mt-5 block text-center text-[13px] text-[#0d6efd] hover:underline">
          Sign out
        </a>
      </Card>
    );
  }

  return (
    <Card>
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#f0f7ef] text-[#1b7f3a]">
        <Check size={24} strokeWidth={3} />
      </div>
      <h1 className="text-center text-[22px] font-bold text-black">Signed in successfully</h1>
      {authRequest ? (
        <p className="mt-3 text-center text-[15px] text-[#777]">You are now signed in. Redirecting...</p>
      ) : (
        <>
          <p className="mx-auto mt-3 max-w-[380px] text-center text-[15px] leading-6 text-[#777]">
            Open the IAM admin console to invite users into systems.
          </p>
          <Button type="button" className="mx-auto mt-5" fullWidth={false} onClick={() => { window.location.href = "/admin"; }}>
            Open admin console
          </Button>
        </>
      )}
    </Card>
  );
}

export default function SignedInPage() {
  return (
    <Suspense fallback={<Card><p className="text-center text-[14px] text-[#777]">Loading...</p></Card>}>
      <SignedInContent />
    </Suspense>
  );
}
