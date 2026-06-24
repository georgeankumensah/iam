"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function LoginNameContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

  const [loginName, setLoginName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const params = new URLSearchParams({ loginName });
      if (authRequest) params.set("authRequest", authRequest);

      const resp = await fetch("/api/login/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ loginName, authRequest }),
      });

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error || "User not found");
      }

      const data = await resp.json();
      router.push(`/password?userId=${data.userId}&loginName=${encodeURIComponent(loginName)}&authRequest=${authRequest}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-6 text-center text-xl font-semibold text-gray-900">Sign in</h2>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit}>
        <Input
          label="Email or Username"
          type="text"
          value={loginName}
          onChange={(e) => setLoginName(e.target.value)}
          placeholder="Enter your email or username"
          autoComplete="username"
          autoFocus
          required
        />
        <Button type="submit" loading={loading}>
          Continue
        </Button>
      </form>
      <p className="mt-4 text-center text-sm text-gray-500">
        <a href={`/register?authRequest=${authRequest}`} className="text-brand-600 hover:text-brand-500">
          Create new account
        </a>
      </p>
    </Card>
  );
}

export default function LoginNamePage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <LoginNameContent />
    </Suspense>
  );
}
