"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { OtpInput } from "@/components/OtpInput";

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
      <h1 className="text-center text-[28px] font-bold text-black">Verify your email</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">Enter the verification code sent to your email.</p>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit} className="mx-auto max-w-[430px]">
        <OtpInput value={verificationCode.replace(/\D/g, "").slice(0, 6)} onChange={setVerificationCode} invalid={Boolean(error)} disabled={loading} autoFocus />
        <Button type="submit" loading={loading} disabled={verificationCode.length !== 6} className="mx-auto mt-6 !h-12 !w-[280px]" fullWidth={false}>Verify email</Button>
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
