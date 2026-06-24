"use client";

import { useState } from "react";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

export default function DeviceAuthPage() {
  const [userCode, setUserCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await fetch("/api/device/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userCode }),
      });
      if (!resp.ok) { const data = await resp.json(); throw new Error(data.error || "Invalid code"); }
      window.location.href = "/signedin";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally { setLoading(false); }
  }

  return (
    <Card>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-900">Device Authorization</h2>
      <p className="mb-6 text-center text-sm text-gray-500">Enter the code displayed on your device</p>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit}>
        <Input label="Device code" type="text" value={userCode} onChange={(e) => setUserCode(e.target.value.toUpperCase())}
          placeholder="XXXX-XXXX" autoFocus required />
        <Button type="submit" loading={loading}>Verify</Button>
      </form>
    </Card>
  );
}
