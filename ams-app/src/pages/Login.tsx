import { useEffect } from "react";
import { useAuth } from "@zitadel/react-auth";

export default function Login() {
  const { signinRedirect, isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      window.location.href = "/";
    }
  }, [isAuthenticated, isLoading]);

  if (isLoading) {
    return (
      <div className="login-page">
        <div className="card">
          <h1>Signing you in...</h1>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  if (isAuthenticated) return null;

  return (
    <div className="login-page">
      <div className="card">
        <h1>Application Management System</h1>
        <p>Sign in to manage your applications</p>
        <button onClick={() => signinRedirect()} className="btn-primary">
          Sign in with Zitadel
        </button>
      </div>
    </div>
  );
}
