import { useEffect } from "react";
import { useAuth } from "@zitadel/react-auth";

export default function Callback() {
  const { isAuthenticated, error } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      window.location.href = "/";
    }
  }, [isAuthenticated]);

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
