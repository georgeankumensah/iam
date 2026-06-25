"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Mail } from "lucide-react";
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
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#f7f7f7] text-[#111]">
            <Mail size={22} />
          </div>
          <h1 className="text-[22px] font-bold text-black">Check your email</h1>
          <p className="mx-auto mt-3 max-w-[380px] text-[15px] leading-6 text-[#777]">If an account exists, you will receive a password reset link.</p>
          <a href={`/login?authRequest=${authRequest}`} className="mt-4 inline-block text-[13px] text-[#0d6efd] hover:underline">Back to sign in</a>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h1 className="text-center text-[28px] font-bold text-black">Reset your password</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">Enter your email address and we&apos;ll send you a reset link.</p>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit} className="mx-auto max-w-[460px]">
        <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" autoComplete="email" autoFocus required />
        <Button type="submit" loading={loading}>Send reset link</Button>
        <p className="mt-4 text-center text-[13px] text-[#777]">
          <a href={`/login?authRequest=${authRequest}`} className="text-[#0d6efd] hover:underline">Back to sign in</a>
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
