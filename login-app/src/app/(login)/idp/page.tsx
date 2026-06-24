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
      <h2 className="mb-6 text-center text-xl font-semibold text-gray-900">Sign in with</h2>
      <div className="space-y-3">
        {IDPS.map((idp) => (
          <button key={idp.id} onClick={() => handleIdpLogin(idp.id)}
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-200 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-xs font-bold">{idp.icon}</span>
            {idp.label}
          </button>
        ))}
      </div>
      <div className="mt-6 text-center">
        <a href={`/login?authRequest=${authRequest}`} className="text-sm text-brand-600 hover:text-brand-500">
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
