"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function PasskeyContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handlePasskeyLogin() {
    setError(null);
    setLoading(true);

    try {
      if (!window.PublicKeyCredential) {
        throw new Error("Passkeys are not supported on this browser");
      }

      const resp = await fetch("/api/passkey/assertion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ authRequest }),
      });

      if (!resp.ok) throw new Error("Failed to start passkey login");

      const options = await resp.json();
      const assertion = await navigator.credentials.get({ publicKey: options.publicKey });

      const verifyResp = await fetch("/api/passkey/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ authRequest, assertion }),
      });

      if (!verifyResp.ok) throw new Error("Passkey verification failed");

      const { redirectUrl } = await verifyResp.json();
      window.location.href = redirectUrl || "/signedin";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Passkey authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Sign in with Passkey</h2>
      <p className="mb-6 text-center text-sm text-gray-500">
        Use your device&apos;s biometric or PIN to sign in securely
      </p>
      <ErrorAlert message={error} className="mb-4" />
      <div className="space-y-4">
        <Button onClick={handlePasskeyLogin} loading={loading}>
          {loading ? "Checking..." : "Use Passkey"}
        </Button>
        <div className="text-center">
          <a href={`/login?authRequest=${authRequest}`} className="text-sm text-brand-600 hover:text-brand-500">
            Use password instead
          </a>
        </div>
      </div>
    </Card>
  );
}

export default function PasskeyPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <PasskeyContent />
    </Suspense>
  );
}
