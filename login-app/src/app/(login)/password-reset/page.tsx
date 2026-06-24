"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function PasswordResetContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await fetch("/api/password-reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, authRequest }),
      });
      if (!resp.ok) { const data = await resp.json(); throw new Error(data.error || "Request failed"); }
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally { setLoading(false); }
  }

  if (success) {
    return (
      <Card>
        <div className="text-center">
          <div className="mb-4 text-4xl">✉️</div>
          <h2 className="mb-2 text-xl font-semibold text-gray-900">Check your email</h2>
          <p className="text-gray-500">If an account exists, you will receive a password reset link.</p>
          <a href={`/login?authRequest=${authRequest}`} className="mt-4 inline-block text-sm text-brand-600 hover:text-brand-500">Back to sign in</a>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Reset your password</h2>
      <p className="mb-6 text-center text-sm text-gray-500">Enter your email address and we&apos;ll send you a reset link</p>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit}>
        <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email" autoComplete="email" autoFocus required />
        <Button type="submit" loading={loading}>Send reset link</Button>
        <p className="mt-4 text-center text-sm text-gray-500">
          <a href={`/login?authRequest=${authRequest}`} className="text-brand-600 hover:text-brand-500">Back to sign in</a>
        </p>
      </form>
    </Card>
  );
}

export default function PasswordResetPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <PasswordResetContent />
    </Suspense>
  );
}
