"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { OtpInput } from "@/components/OtpInput";

function MfaTotpContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const signedInUrl = authRequest ? `/signedin?authRequest=${encodeURIComponent(authRequest)}` : "/signedin";

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const resp = await fetch("/api/mfa/totp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, authRequest }),
      });

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error || "Invalid code");
      }

      const { redirectUrl } = await resp.json();
      window.location.href = redirectUrl || signedInUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h1 className="text-center text-[28px] font-bold text-black">Authenticator Code</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">
        Enter the 6-digit code from your authenticator app.
      </p>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit} className="mx-auto max-w-[430px]">
        <OtpInput value={code} onChange={setCode} invalid={Boolean(error)} disabled={loading} autoFocus />
        <Button type="submit" loading={loading} disabled={code.length !== 6} className="mx-auto mt-6 !h-12 !w-[280px]" fullWidth={false}>
          Verify Code
        </Button>
      </form>
    </Card>
  );
}

export default function MfaTotpPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <MfaTotpContent />
    </Suspense>
  );
}
