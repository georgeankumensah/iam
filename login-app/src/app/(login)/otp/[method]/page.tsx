"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { OtpInput } from "@/components/OtpInput";

function OTPContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const method = params.method as string;
  const authRequest = searchParams.get("authRequest") || "";
  const signedInUrl = authRequest ? `/signedin?authRequest=${encodeURIComponent(authRequest)}` : "/signedin";
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const methodLabel = method === "sms" ? "SMS" : "Email";

  // Ask Zitadel to send the code as soon as the challenge page opens.
  useEffect(() => {
    fetch(`/api/otp/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "request", authRequest }),
    })
      .then(async (resp) => {
        if (!resp.ok) {
          const data = await resp.json();
          setError(data.error || `Could not send ${methodLabel} code`);
        }
      })
      .catch(() => setError(`Could not send ${methodLabel} code`));
  }, [method, authRequest, methodLabel]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await fetch(`/api/otp/${method}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, authRequest }),
      });
      if (!resp.ok) { const data = await resp.json(); throw new Error(data.error || `Invalid ${methodLabel} code`); }
      const { redirectUrl } = await resp.json();
      window.location.href = redirectUrl || signedInUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally { setLoading(false); }
  }

  return (
    <Card>
      <h1 className="text-center text-[28px] font-bold text-black">{methodLabel} Verification</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">
        Enter the 6-digit verification code sent to your {methodLabel.toLowerCase()}.
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

export default function OTPPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <OTPContent />
    </Suspense>
  );
}
