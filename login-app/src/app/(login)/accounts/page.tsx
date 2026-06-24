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
      <h2 className="mb-6 text-center text-xl font-semibold text-gray-900">Choose an account</h2>
      <div className="space-y-3">
        {accounts.map((account) => (
          <button key={account.id} onClick={() => handleSelect(account.id)}
            className="flex w-full items-center gap-3 rounded-lg border border-gray-200 p-4 text-left hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 text-sm font-medium text-brand-700">
              {account.name.charAt(0)}
            </div>
            <div>
              <p className="font-medium text-gray-900">{account.name}</p>
              <p className="text-sm text-gray-500">{account.label}</p>
            </div>
          </button>
        ))}
      </div>
      <div className="mt-6">
        <Button variant="secondary" onClick={() => router.push(`/loginname?authRequest=${authRequest}`)}>
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
