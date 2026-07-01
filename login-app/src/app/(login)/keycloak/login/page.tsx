"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Input } from "@/components/Input";
import { PasswordInput } from "@/components/PasswordInput";

function KeycloakLoginContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const redirectUri = searchParams.get("redirect_uri") || "";
  const state = searchParams.get("state") || "";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const resp = await fetch("/api/auth/jwt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          password,
          authRequest,
          redirectUri,
          state,
        }),
      });

      if (resp.redirected && resp.url) {
        window.location.href = resp.url;
        return;
      }

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.error || "Authentication failed");
      }

      const data = await resp.json();
      if (data.redirectUrl) {
        window.location.href = data.redirectUrl;
      } else {
        throw new Error("Unexpected response");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <div className="text-center">
        <h1 className="text-[22px] font-bold text-black">Keycloak Sign In</h1>
        <p className="mx-auto mt-3 max-w-[420px] text-[15px] leading-6 text-[#999]">
          Authenticate with your Keycloak credentials.
        </p>
      </div>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit} className="mx-auto mt-8 max-w-[460px] space-y-4">
        <Input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username or email"
          autoComplete="username"
          autoFocus
          required
        />
        <PasswordInput
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoComplete="current-password"
          required
        />
        <Button type="submit" loading={loading} className="mt-7">
          Sign In with Keycloak
        </Button>
      </form>
    </Card>
  );
}

export default function KeycloakLoginPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <KeycloakLoginContent />
    </Suspense>
  );
}
