"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Fingerprint, KeyRound } from "lucide-react";
import { Card } from "@/components/Card";
import { ErrorAlert } from "@/components/ErrorAlert";
import { prepareCreationOptions, serializeCredential } from "@/lib/webauthn";

function SetAuthenticatorContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function setupPasskey() {
    setError(null);
    setLoading(true);

    try {
      if (!window.PublicKeyCredential) {
        throw new Error("Passkeys are not supported on this browser");
      }

      const resp = await fetch("/api/authenticator/passkey/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ authRequest }),
      });

      if (!resp.ok) throw new Error("Failed to start passkey registration");

      const { passkeyId, publicKey } = await resp.json();
      const credential = (await navigator.credentials.create({
        publicKey: prepareCreationOptions(publicKey),
      })) as PublicKeyCredential;

      const verifyResp = await fetch("/api/authenticator/passkey/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passkeyId, credential: serializeCredential(credential) }),
      });

      if (!verifyResp.ok) throw new Error("Passkey registration failed");

      // Passkey registered; satisfy the session's MFA requirement via the
      // normal passkey challenge.
      window.location.href = `/passkey?authRequest=${authRequest}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setLoading(false);
    }
  }

  function setupTOTP() {
    // TOTP enrollment needs a QR + code-entry step, handled on its own page.
    window.location.href = `/authenticator/totp?authRequest=${authRequest}`;
  }

  return (
    <>
      <h1 className="text-center text-[28px] font-bold text-black">Set up authenticator</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">
        Choose an authentication method to secure your account.
      </p>
      <ErrorAlert message={error} className="mb-4" />
      <div className="space-y-3">
        <button
          onClick={setupPasskey}
          disabled={loading}
          className="flex w-full items-center gap-4 rounded-[10px] border border-[#d1d5db] bg-white p-4 text-left transition hover:bg-[#f8f8f8] disabled:opacity-50"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#f7f7f7] text-[#111]">
            <Fingerprint size={18} />
          </span>
          <span>
            <span className="block text-[14px] font-semibold text-black">Passkey</span>
            <span className="block text-[12px] leading-5 text-[#777]">Use biometric or PIN</span>
          </span>
        </button>
        <button
          onClick={setupTOTP}
          disabled={loading}
          className="flex w-full items-center gap-4 rounded-[10px] border border-[#d1d5db] bg-white p-4 text-left transition hover:bg-[#f8f8f8] disabled:opacity-50"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#f7f7f7] text-[#111]">
            <KeyRound size={18} />
          </span>
          <span>
            <span className="block text-[14px] font-semibold text-black">Authenticator App</span>
            <span className="block text-[12px] leading-5 text-[#777]">Use TOTP codes</span>
          </span>
        </button>
      </div>
    </>
  );
}

export default function SetAuthenticatorPage() {
  return (
    <Card>
      <Suspense fallback={<div className="text-center">Loading...</div>}>
        <SetAuthenticatorContent />
      </Suspense>
    </Card>
  );
}
