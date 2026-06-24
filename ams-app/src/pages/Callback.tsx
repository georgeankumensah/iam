import { useEffect } from "react";
import { useAuth } from "@rfdtech/oidc-client/react";

export default function Callback() {
  const { is_authenticated, error } = useAuth();

  useEffect(() => {
    if (is_authenticated) {
      window.location.href = "/";
    }
  }, [is_authenticated]);

  if (error) {
    return (
      <div className="login-page">
        <div className="card card-error">
          <h1>Authentication Failed</h1>
          <p>{error.message}</p>
          <button onClick={() => (window.location.href = "/login?silent=false")} className="btn-primary">
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
