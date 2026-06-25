"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { KeyRound } from "lucide-react";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { prepareRequestOptions, serializeAssertion } from "@/lib/webauthn";

function U2FContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const signedInUrl = authRequest ? `/signedin?authRequest=${encodeURIComponent(authRequest)}` : "/signedin";
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
      window.location.href = redirectUrl || signedInUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Security key verification failed");
    } finally { setLoading(false); }
  }

  return (
    <Card>
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#f7f7f7] text-[#111]">
        <KeyRound size={22} />
      </div>
      <h1 className="text-center text-[28px] font-bold text-black">Security Key</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">Insert and tap your security key.</p>
      <ErrorAlert message={error} className="mb-4" />
      <Button onClick={handleU2F} loading={loading} className="mx-auto max-w-[360px]">{loading ? "Waiting for key..." : "Tap Security Key"}</Button>
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
