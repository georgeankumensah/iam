"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
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
        publicKey: prepareCreationOptions({ publicKey }),
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
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Set up authenticator</h2>
      <p className="mb-6 text-center text-sm text-gray-500">
        Choose an authentication method to secure your account
      </p>
      <ErrorAlert message={error} className="mb-4" />
      <div className="space-y-3">
        <button
          onClick={setupPasskey}
          disabled={loading}
          className="flex w-full items-center gap-4 rounded-lg border border-gray-200 p-4 text-left hover:bg-gray-50 disabled:opacity-50"
        >
          <span className="text-2xl">🔐</span>
          <div>
            <p className="font-medium text-gray-900">Passkey</p>
            <p className="text-sm text-gray-500">Use biometric or PIN</p>
          </div>
        </button>
        <button
          onClick={setupTOTP}
          disabled={loading}
          className="flex w-full items-center gap-4 rounded-lg border border-gray-200 p-4 text-left hover:bg-gray-50 disabled:opacity-50"
        >
          <span className="text-2xl">🔑</span>
          <div>
            <p className="font-medium text-gray-900">Authenticator App</p>
            <p className="text-sm text-gray-500">Use TOTP codes</p>
          </div>
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
