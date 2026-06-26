"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { PasswordInput } from "@/components/PasswordInput";
import { Input } from "@/components/Input";

function InviteContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("t") || "";
  const code = searchParams.get("code") || "";
  const email = searchParams.get("email") || "";

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!firstName.trim()) {
      setError("First name is required");
      return;
    }
    if (!lastName.trim()) {
      setError("Last name is required");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      const resp = await fetch("/api/invite/accept", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, code, password, firstName, lastName }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error || "Could not accept invitation");
      }
      const { systemUrl } = await resp.json();
      // Send the user to their system to sign in (MFA enrollment follows).
      window.location.href = systemUrl || "/login";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept invitation");
    } finally {
      setLoading(false);
    }
  }

  if (!token || !code) {
    return (
      <Card>
        <div className="text-center text-[14px] text-[#777]">This invitation link is invalid or incomplete.</div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="text-center">
        <h1 className="text-[28px] font-bold text-black">Complete Your Account Setup</h1>
        <p className="mx-auto mt-3 max-w-[500px] text-[15px] leading-6 text-[#999]">
          You have been invited to access a CLET system. Fill in your details and set a password to activate your account.
        </p>
      </div>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit} className="mx-auto mt-7 max-w-[500px] space-y-4">
        <p className="text-[15px] font-semibold text-black">Your Details</p>
        <Input
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          placeholder="First name"
          autoComplete="given-name"
          autoFocus
          required
        />
        <Input
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          placeholder="Last name"
          autoComplete="family-name"
          required
        />
        {email && (
          <Input
            value={email}
            placeholder="Email"
            autoComplete="email"
            disabled
            className="opacity-60"
          />
        )}
        <p className="text-[15px] font-semibold text-black">Set Your Password</p>
        <PasswordInput
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoComplete="new-password"
          required
        />
        <PasswordInput
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Confirm Password"
          autoComplete="new-password"
          required
        />
        <Button type="submit" loading={loading} disabled={!firstName || !lastName || !password || !confirm}>
          Activate account
        </Button>
      </form>
    </Card>
  );
}

export default function InvitePage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <InviteContent />
    </Suspense>
  );
}
