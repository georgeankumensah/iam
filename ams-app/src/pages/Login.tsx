import { useEffect } from "react";
import { useAuth } from "@clet/oidc-client/react";

export default function Login() {
  const { login, is_authenticated, is_loading } = useAuth();

  useEffect(() => {
    if (is_loading) return;
    if (is_authenticated) {
      window.location.href = "/";
    }
  }, [is_authenticated, is_loading]);

  if (is_loading) {
    return (
      <div className="login-page">
        <div className="card">
          <h1>Signing you in...</h1>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  if (is_authenticated) return null;

  return (
    <div className="login-page">
      <div className="card">
        <h1>Application Management System</h1>
        <p>Sign in to manage your applications</p>
        <button onClick={() => login()} className="btn-primary">
          Sign in with Zitadel
        </button>
      </div>
    </div>
  );
}
