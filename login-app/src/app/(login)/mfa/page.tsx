"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { KeyRound, Mail, Smartphone } from "lucide-react";
import { Card } from "@/components/Card";

function MFAContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

  const factors = [
    { id: "totp", label: "Authenticator App", description: "Use a TOTP code from your authenticator app", icon: KeyRound },
    { id: "sms", label: "SMS Code", description: "Receive a code via SMS", icon: Smartphone },
    { id: "email", label: "Email Code", description: "Receive a code via email", icon: Mail },
  ];

  function handleSelect(factorId: string) {
    const path = factorId === "totp" ? `/mfa/totp` : `/otp/${factorId}`;
    router.push(`${path}?authRequest=${authRequest}`);
  }

  return (
    <Card>
      <h1 className="text-center text-[28px] font-bold text-black">Verify your identity</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">
        Choose a verification method
      </p>
      <div className="space-y-3">
        {factors.map((factor) => {
          const Icon = factor.icon;
          return (
            <button
              key={factor.id}
              onClick={() => handleSelect(factor.id)}
              className="flex w-full items-center gap-4 rounded-[10px] border border-[#d1d5db] bg-white p-4 text-left transition hover:bg-[#f8f8f8] focus:border-[#111] focus:outline-none"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#f7f7f7] text-[#111]">
                <Icon size={18} />
              </span>
              <span>
                <span className="block text-[14px] font-semibold text-black">{factor.label}</span>
                <span className="block text-[12px] leading-5 text-[#777]">{factor.description}</span>
              </span>
            </button>
          );
        })}
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
