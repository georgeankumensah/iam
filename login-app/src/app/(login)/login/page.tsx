"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { PasswordInput } from "@/components/PasswordInput";

function LoginContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";
  const signedInUrl = authRequest ? `/signedin?authRequest=${encodeURIComponent(authRequest)}` : "/signedin";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    async function trySilentAuth() {
      try {
        const authResp = await fetch(`/api/auth-request?id=${encodeURIComponent(authRequest)}`);
        if (!authResp.ok) {
          setCheckingSession(false);
          return;
        }
        const data = await authResp.json();
        const prompt = data.prompt || [];
        if (!prompt.includes("PROMPT_NONE")) {
          setCheckingSession(false);
          return;
        }
        const silentResp = await fetch("/api/login/silent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ authRequest }),
        });
        if (silentResp.ok) {
          const { redirectUrl } = await silentResp.json();
          window.location.href = redirectUrl || signedInUrl;
          return;
        }
        const redirectUri = data.redirectUri || "";
        const errParams = new URLSearchParams({
          error: "login_required",
          error_description: "Authentication required",
        });
        if (redirectUri) {
          window.location.href = `${redirectUri}?${errParams}`;
          return;
        }
        setCheckingSession(false);
      } catch {
        setCheckingSession(false);
      }
    }

    if (authRequest) {
      trySilentAuth();
    } else {
      setCheckingSession(false);
    }
  }, [authRequest]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const resp = await fetch("/api/login/authenticate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password, authRequest }),
      });

      if (!resp.ok) {
        throw new Error("Invalid email or password");
      }

      const { next, factors, redirectUrl } = await resp.json();

      if (next === "mfa" && factors?.length) {
        // Route to the preferred second-factor challenge.
        window.location.href = factors[0].path;
        return;
      }
      if (next === "enroll") {
        window.location.href = `/authenticator/set?authRequest=${authRequest}`;
        return;
      }
      window.location.href = redirectUrl || signedInUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  if (checkingSession) {
    return (
      <Card>
        <div className="py-8 text-center text-[14px] text-[#777]">Checking your session...</div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="text-center">
        <h1 className="text-[22px] font-bold text-black">Welcome Back</h1>
        <p className="mx-auto mt-3 max-w-[420px] text-[15px] leading-6 text-[#999]">
          Sign in to your account to access CLET services securely from this browser.
        </p>
      </div>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit} className="mx-auto mt-8 max-w-[460px] space-y-4">
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          autoComplete="email"
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
        <div className="flex items-center justify-between text-[12px]">
          <label className="flex items-center gap-2 text-[#777]">
            <input type="checkbox" className="h-3.5 w-3.5 rounded accent-[#111]" />
            Remember me
          </label>
          <a
            href={`/password-reset?authRequest=${authRequest}`}
            className="text-[#111] hover:underline"
          >
            Forgot your password?
          </a>
        </div>
        <Button type="submit" loading={loading} className="mt-7">
          Sign In
        </Button>
      </form>

    </Card>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <LoginContent />
    </Suspense>
  );
}
