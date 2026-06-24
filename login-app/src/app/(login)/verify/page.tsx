"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function VerifyContent() {
  const searchParams = useSearchParams();
  const codeParam = searchParams.get("code") || "";
  const userId = searchParams.get("userId") || "";
  const [verificationCode, setVerificationCode] = useState(codeParam);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: verificationCode, userId }),
      });
      if (!resp.ok) { const data = await resp.json(); throw new Error(data.error || "Verification failed"); }
      window.location.href = "/signedin";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally { setLoading(false); }
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Verify your email</h2>
      <p className="mb-6 text-center text-sm text-gray-500">Enter the verification code sent to your email</p>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit}>
        <Input label="Verification code" type="text" value={verificationCode} onChange={(e) => setVerificationCode(e.target.value)}
          placeholder="Enter code" autoComplete="one-time-code" autoFocus required />
        <Button type="submit" loading={loading}>Verify email</Button>
      </form>
    </Card>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <VerifyContent />
    </Suspense>
  );
}
