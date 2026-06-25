"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { prepareRequestOptions, serializeAssertion } from "@/lib/webauthn";

function U2FContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleU2F() {
    setError(null);
    setLoading(true);
    try {
      if (!window.PublicKeyCredential) {
        throw new Error("Security keys are not supported on this browser");
      }

      const resp = await fetch("/api/u2f/assertion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ authRequest }),
      });
      if (!resp.ok) throw new Error("Failed to start security key verification");

      const options = await resp.json();
      const credential = (await navigator.credentials.get({
        publicKey: prepareRequestOptions(options),
      })) as PublicKeyCredential;

      const verifyResp = await fetch("/api/u2f/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ authRequest, assertion: serializeAssertion(credential) }),
      });
      if (!verifyResp.ok) throw new Error("Security key verification failed");

      const { redirectUrl } = await verifyResp.json();
      window.location.href = redirectUrl || "/signedin";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Security key verification failed");
    } finally { setLoading(false); }
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Security Key</h2>
      <p className="mb-6 text-center text-sm text-gray-500">Insert and tap your security key</p>
      <ErrorAlert message={error} className="mb-4" />
      <Button onClick={handleU2F} loading={loading}>{loading ? "Waiting for key..." : "Tap Security Key"}</Button>
    </Card>
  );
}

export default function U2FPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <U2FContent />
    </Suspense>
  );
}
