"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const [form, setForm] = useState({ email: "", firstName: "", lastName: "", password: "", confirmPassword: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function updateField(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (form.password !== form.confirmPassword) { setError("Passwords do not match"); return; }
    if (form.password.length < 12) { setError("Password must be at least 12 characters"); return; }
    setLoading(true);

    try {
      const resp = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, authRequest }),
      });
      if (!resp.ok) { const data = await resp.json(); throw new Error(data.error || "Registration failed"); }
      router.push(`/signedin?authRequest=${authRequest}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally { setLoading(false); }
  }

  return (
    <Card>
      <h2 className="mb-6 text-center text-xl font-semibold text-gray-900">Create account</h2>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="Email" type="email" value={form.email} onChange={(e) => updateField("email", e.target.value)} autoComplete="email" autoFocus required />
        <div className="grid grid-cols-2 gap-4">
          <Input label="First name" type="text" value={form.firstName} onChange={(e) => updateField("firstName", e.target.value)} autoComplete="given-name" required />
          <Input label="Last name" type="text" value={form.lastName} onChange={(e) => updateField("lastName", e.target.value)} autoComplete="family-name" required />
        </div>
        <Input label="Password" type="password" value={form.password} onChange={(e) => updateField("password", e.target.value)} autoComplete="new-password" required />
        <Input label="Confirm password" type="password" value={form.confirmPassword} onChange={(e) => updateField("confirmPassword", e.target.value)} autoComplete="new-password" required />
        <Button type="submit" loading={loading}>Create account</Button>
        <p className="text-center text-sm text-gray-500">
          Already have an account?{" "}
          <a href={`/loginname?authRequest=${authRequest}`} className="text-brand-600 hover:text-brand-500">Sign in</a>
        </p>
      </form>
    </Card>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <RegisterContent />
    </Suspense>
  );
}
