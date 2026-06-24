import { useEffect } from "react";
import { redirectToLogin, silentLogin } from "../lib/oidc";

export default function Login() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("silent") !== "false") {
      silentLogin();
    }
  }, []);

  const showButton = new URLSearchParams(window.location.search).get("silent") === "false";

  if (!showButton) {
    return (
      <div className="login-page">
        <div className="card">
          <h1>Signing you in...</h1>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="card">
        <h1>NBES</h1>
        <p>Notification &amp; Broadcast Exchange Service</p>
        <button onClick={redirectToLogin} className="btn-primary">
          Sign in with Zitadel
        </button>
      </div>
    </div>
  );
}
