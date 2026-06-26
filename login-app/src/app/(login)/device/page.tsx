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
      <h1 className="text-center text-[28px] font-bold text-black">Device Authorization</h1>
      <p className="mx-auto mb-7 mt-4 max-w-[430px] text-center text-[15px] leading-6 text-[#999]">Enter the code displayed on your device.</p>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit} className="mx-auto max-w-[460px] space-y-4">
        <Input type="text" value={userCode} onChange={(e) => setUserCode(e.target.value.toUpperCase())}
          placeholder="XXXX-XXXX" autoFocus required />
        <Button type="submit" loading={loading}>Verify</Button>
      </form>
    </Card>
  );
}
