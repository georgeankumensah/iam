"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function TotpEnrollContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

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
      window.location.href = redirectUrl || "/signedin";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Set up authenticator app</h2>
      <p className="mb-4 text-center text-sm text-gray-500">
        Scan this QR code with your authenticator app, then enter the 6-digit code.
      </p>
      <ErrorAlert message={error} className="mb-4" />

      <div className="mb-4 flex justify-center">
        {uri ? (
          <QRCodeSVG value={uri} size={180} includeMargin />
        ) : (
          <div className="text-sm text-gray-400">Generating QR code…</div>
        )}
      </div>

      {secret && (
        <p className="mb-4 break-all text-center text-xs text-gray-500">
          Can&apos;t scan? Enter this key manually:
          <br />
          <code className="font-mono">{secret}</code>
        </p>
      )}

      <form onSubmit={handleSubmit}>
        <Input
          label="Verification code"
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
          placeholder="000000"
          inputMode="numeric"
          autoComplete="one-time-code"
          autoFocus
          required
        />
        <Button type="submit" loading={loading} disabled={!uri}>
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
