"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";

const IDPS = [
  { id: "google", label: "Google", icon: "G" },
  { id: "github", label: "GitHub", icon: "GH" },
  { id: "microsoft", label: "Microsoft", icon: "MS" },
];

function IdpContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

  function handleIdpLogin(idpId: string) {
    window.location.href = `/idps/callback/${idpId}?authRequest=${authRequest}`;
  }

  return (
    <Card>
      <h1 className="text-center text-[28px] font-bold text-black">Sign in with</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">
        Choose an identity provider to continue.
      </p>
      <div className="space-y-3">
        {IDPS.map((idp) => (
          <button key={idp.id} onClick={() => handleIdpLogin(idp.id)}
            className="flex w-full items-center justify-center gap-3 rounded-[10px] border border-[#d1d5db] bg-white px-4 py-3 text-[13px] font-semibold text-[#111] transition hover:bg-[#f8f8f8] focus:border-[#111] focus:outline-none">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f7f7f7] text-[11px] font-bold">{idp.icon}</span>
            {idp.label}
          </button>
        ))}
      </div>
      <div className="mt-6 text-center">
        <a href={`/login?authRequest=${authRequest}`} className="text-[13px] text-[#0d6efd] hover:underline">
          Sign in with email and password
        </a>
      </div>
    </Card>
  );
}

export default function IdpPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <IdpContent />
    </Suspense>
  );
}
