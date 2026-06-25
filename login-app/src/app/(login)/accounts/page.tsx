"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";

function AccountsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

  const accounts = [{ id: "user-1", label: "admin@clet.gov.gh", name: "Admin User" }];

  function handleSelect(userId: string) {
    router.push(`/password?userId=${userId}&authRequest=${authRequest}`);
  }

  return (
    <Card>
      <h1 className="text-center text-[28px] font-bold text-black">Choose an account</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">
        Select the account you want to continue with.
      </p>
      <div className="space-y-3">
        {accounts.map((account) => (
          <button key={account.id} onClick={() => handleSelect(account.id)}
            className="flex w-full items-center gap-3 rounded-[10px] border border-[#d1d5db] bg-white p-4 text-left transition hover:bg-[#f8f8f8] focus:border-[#111] focus:outline-none">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#f7f7f7] text-[13px] font-semibold text-[#111]">
              {account.name.charAt(0)}
            </div>
            <div>
              <p className="text-[14px] font-semibold text-black">{account.name}</p>
              <p className="text-[12px] text-[#777]">{account.label}</p>
            </div>
          </button>
        ))}
      </div>
      <div className="mt-6">
        <Button variant="secondary" onClick={() => router.push(`/login?authRequest=${authRequest}`)}>
          Use another account
        </Button>
      </div>
    </Card>
  );
}

export default function AccountsPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <AccountsContent />
    </Suspense>
  );
}
