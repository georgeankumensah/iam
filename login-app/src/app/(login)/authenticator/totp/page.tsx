"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { OtpInput } from "@/components/OtpInput";

function TotpEnrollContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const signedInUrl = authRequest ? `/signedin?authRequest=${encodeURIComponent(authRequest)}` : "/signedin";

  const [uri, setUri] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Start enrollment on load: fetch the otpauth URI + secret for the QR code.
  useEffect(() => {
    async function start() {
      try {
        const resp = await fetch("/api/authenticator/totp/setup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ authRequest }),
        });
        if (!resp.ok) throw new Error("Could not start authenticator setup");
        const data = await resp.json();
        setUri(data.uri);
        setSecret(data.secret);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Setup failed");
      }
    }
    start();
  }, [authRequest]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await fetch("/api/authenticator/totp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, authRequest }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error || "Invalid code");
      }
      const { redirectUrl, next, redirectTo } = await resp.json();
      if (next === "mfa" && redirectTo) {
        window.location.href = redirectTo;
        return;
      }
      window.location.href = redirectUrl || signedInUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h1 className="text-center text-[28px] font-bold text-black">Set up authenticator app</h1>
      <p className="mx-auto mb-6 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">
        Scan this QR code with your authenticator app, then enter the 6-digit code.
      </p>
      <ErrorAlert message={error} className="mb-4" />

      <div className="mb-4 flex justify-center">
        {uri ? (
          <QRCodeSVG value={uri} size={180} includeMargin />
        ) : (
          <div className="text-[13px] text-[#999]">Generating QR code...</div>
        )}
      </div>

      {secret && (
        <p className="mb-5 break-all text-center text-[12px] leading-5 text-[#777]">
          Can&apos;t scan? Enter this key manually:
          <br />
          <code className="font-mono">{secret}</code>
        </p>
      )}

      <form onSubmit={handleSubmit} className="mx-auto max-w-[430px]">
        <OtpInput value={code} onChange={setCode} invalid={Boolean(error)} disabled={loading || !uri} autoFocus />
        <Button type="submit" loading={loading} disabled={!uri || code.length !== 6} className="mx-auto mt-6 !h-12 !w-[280px]" fullWidth={false}>
          Verify &amp; continue
        </Button>
      </form>
    </Card>
  );
}

export default function TotpEnrollPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <TotpEnrollContent />
    </Suspense>
  );
}
