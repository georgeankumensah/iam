import { useEffect, useState } from "react";
import { exchangeCode, storeToken } from "../lib/oidc";

export default function Callback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    const errorParam = params.get("error");

    if (errorParam) {
      sessionStorage.removeItem("oidc_state");
      sessionStorage.removeItem("oidc_verifier");
      window.location.href = "/login?silent=false";
      return;
    }

    if (!code || !state) {
      setError("Missing code or state parameter");
      return;
    }

    const storedState = sessionStorage.getItem("oidc_state");
    const verifier = sessionStorage.getItem("oidc_verifier");

    sessionStorage.removeItem("oidc_state");
    sessionStorage.removeItem("oidc_verifier");

    if (!verifier) {
      setError("No PKCE verifier found — restart login");
      return;
    }

    exchangeCode(code, state, storedState || "", verifier)
      .then((tokenData) => {
        storeToken(tokenData);
        window.location.href = "/";
      })
      .catch((err: Error) => {
        setError(err.message);
      });
  }, []);

  if (error) {
    return (
      <div className="login-page">
        <div className="card card-error">
          <h1>Authentication Failed</h1>
          <p>{error}</p>
          <button onClick={() => (window.location.href = "/")} className="btn-primary">
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="card">
        <h1>Signing you in...</h1>
        <div className="spinner" />
      </div>
    </div>
  );
}
