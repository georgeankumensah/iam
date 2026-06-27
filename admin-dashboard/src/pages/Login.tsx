import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "@rfdtech/oidc-client/react";

export function Login() {
  const { login, is_loading, error } = useAuth();
  const [signing_in, set_signing_in] = useState(false);

  const handleLogin = async () => {
    set_signing_in(true);
    try {
      await login();
    } catch {
      set_signing_in(false);
    }
  };

  const busy = is_loading || signing_in;

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f4f6f2]">
      <div className="w-full max-w-sm rounded-lg border border-[#d8ded3] bg-white p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#d6ff6b] text-[#101915]">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[#18211d]">CLET IAM Control</h1>
            <p className="text-xs text-[#667267]">Superadmin dashboard</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-[#f2dede] bg-[#fef2f2] px-4 py-3 text-xs text-[#8b3a3a]">
            {error instanceof Error ? error.message : String(error)}
          </div>
        )}

        <button
          type="button"
          onClick={handleLogin}
          disabled={busy}
          className="w-full rounded-md bg-[#18211d] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#2a362f] disabled:opacity-50"
        >
          {busy ? "Redirecting…" : "Sign in with Zitadel"}
        </button>
      </div>
    </main>
  );
}
