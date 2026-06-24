"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function PasswordContent() {
  const searchParams = useSearchParams();
  const userId = searchParams.get("userId") || "";
  const authRequest = searchParams.get("authRequest") || "";
  const loginName = searchParams.get("loginName") || "";

  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const resp = await fetch("/api/login/authenticate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId, password, authRequest }),
      });

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error || "Authentication failed");
      }

      const { redirectUrl } = await resp.json();
      window.location.href = redirectUrl || "/signedin";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Enter password</h2>
      {loginName && (
        <p className="mb-6 text-center text-sm text-gray-500">{loginName}</p>
      )}
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit}>
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter your password"
          autoComplete="current-password"
          autoFocus
          required
        />
        <div className="mb-4 text-right">
          <a
            href={`/password-reset?authRequest=${authRequest}`}
            className="text-sm text-brand-600 hover:text-brand-500"
          >
            Forgot password?
          </a>
        </div>
        <Button type="submit" loading={loading}>
          Sign in
        </Button>
      </form>
    </Card>
  );
}

export default function PasswordPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <PasswordContent />
    </Suspense>
  );
}
