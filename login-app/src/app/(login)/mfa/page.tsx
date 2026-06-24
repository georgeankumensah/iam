"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";

function MFAContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

  const factors = [
    { id: "totp", label: "Authenticator App", description: "Use a TOTP code from your authenticator app", icon: "🔑" },
    { id: "sms", label: "SMS Code", description: "Receive a code via SMS", icon: "📱" },
    { id: "email", label: "Email Code", description: "Receive a code via email", icon: "📧" },
  ];

  function handleSelect(factorId: string) {
    const path = factorId === "totp" ? `/mfa/totp` : `/otp/${factorId}`;
    router.push(`${path}?authRequest=${authRequest}`);
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Verify your identity</h2>
      <p className="mb-6 text-center text-sm text-gray-500">
        Choose a verification method
      </p>
      <div className="space-y-3">
        {factors.map((factor) => (
          <button
            key={factor.id}
            onClick={() => handleSelect(factor.id)}
            className="flex w-full items-center gap-4 rounded-lg border border-gray-200 p-4 text-left hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <span className="text-2xl">{factor.icon}</span>
            <div>
              <p className="font-medium text-gray-900">{factor.label}</p>
              <p className="text-sm text-gray-500">{factor.description}</p>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
}

export default function MFAPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <MFAContent />
    </Suspense>
  );
}
