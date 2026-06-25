"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Fingerprint } from "lucide-react";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { prepareRequestOptions, serializeAssertion } from "@/lib/webauthn";

function PasskeyContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const signedInUrl = authRequest ? `/signedin?authRequest=${encodeURIComponent(authRequest)}` : "/signedin";
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
      const credential = (await navigator.credentials.get({
        publicKey: prepareRequestOptions(options),
      })) as PublicKeyCredential;

      const verifyResp = await fetch("/api/passkey/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ authRequest, assertion: serializeAssertion(credential) }),
      });

      if (!verifyResp.ok) throw new Error("Passkey verification failed");

      const { redirectUrl } = await verifyResp.json();
      window.location.href = redirectUrl || signedInUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Passkey authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#f7f7f7] text-[#111]">
        <Fingerprint size={24} />
      </div>
      <h1 className="text-center text-[28px] font-bold text-black">Sign in with Passkey</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">
        Use your device&apos;s biometric or PIN to sign in securely.
      </p>
      <ErrorAlert message={error} className="mb-4" />
      <div className="mx-auto max-w-[360px] space-y-4">
        <Button onClick={handlePasskeyLogin} loading={loading}>
          {loading ? "Checking..." : "Use Passkey"}
        </Button>
        <div className="text-center">
          <a href={`/login?authRequest=${authRequest}`} className="text-[13px] text-[#0d6efd] hover:underline">
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
