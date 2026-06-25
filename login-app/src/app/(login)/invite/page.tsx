"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function InviteContent() {
  const searchParams = useSearchParams();
  const userId = searchParams.get("userID") || searchParams.get("userId") || "";
  const code = searchParams.get("code") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
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
        body: JSON.stringify({ userId, code, password }),
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

  if (!userId || !code) {
    return (
      <Card>
        <div className="text-center text-gray-500">This invitation link is invalid or incomplete.</div>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Accept your invitation</h2>
      <p className="mb-6 text-center text-sm text-gray-500">Set a password to activate your account.</p>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit}>
        <Input
          label="New password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          autoFocus
          required
        />
        <Input
          label="Confirm password"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoComplete="new-password"
          required
        />
        <Button type="submit" loading={loading}>
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
