"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";

function LoginContent() {
  const searchParams = useSearchParams();
  const authRequest = searchParams.get("authRequest") || "";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
          window.location.href = redirectUrl || "/signedin";
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

      const { redirectUrl } = await resp.json();
      window.location.href = redirectUrl || "/signedin";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  if (checkingSession) {
    return (
      <Card>
        <div className="text-center py-8 text-gray-500">Checking your session...</div>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="mb-6 text-center text-xl font-semibold text-gray-900">Sign in</h2>
      <ErrorAlert message={error} className="mb-4" />
      <form onSubmit={handleSubmit}>
        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email"
          autoComplete="email"
          autoFocus
          required
        />
        <div className="mb-4">
          <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
              required
              className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              tabIndex={-1}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>
        </div>
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

export default function LoginPage() {
  return (
    <Suspense fallback={<Card><div className="text-center">Loading...</div></Card>}>
      <LoginContent />
    </Suspense>
  );
}
