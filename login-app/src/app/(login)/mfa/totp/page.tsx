"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function MfaTotpContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

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
      window.location.href = redirectUrl || "/signedin";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Authenticator Code</h2>
      <p className="mb-6 text-center text-sm text-gray-500">
        Enter the 6-digit code from your authenticator app
      </p>
      <ErrorAlert message={error} className="mb-4" />
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
        <Button type="submit" loading={loading}>
          Verify
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
