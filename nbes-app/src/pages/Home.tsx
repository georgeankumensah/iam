import { useEffect, useState } from "react";
import { jwtDecode } from "jwt-decode";
import { getStoredToken, logout, fetchUserinfo } from "../lib/oidc";

interface UserClaims {
  sub: string;
  email?: string;
  name?: string;
  preferred_username?: string;
}

export default function Home() {
  const [user, setUser] = useState<UserClaims | null>(null);
  const [userinfo, setUserinfo] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    try {
      const claims = jwtDecode<UserClaims>(token.id_token);
      setUser(claims);
    } catch {
      setError("Failed to decode ID token");
      return;
    }

    fetchUserinfo(token.access_token)
      .then(setUserinfo)
      .catch(() => setUserinfo(null));
  }, []);

  if (error) {
    return (
      <div className="login-page">
        <div className="card card-error">
          <h1>Error</h1>
          <p>{error}</p>
          <button onClick={logout} className="btn-primary">
            Back to login
          </button>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="login-page">
        <div className="card">
          <h1>Loading...</h1>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="home-page">
      <header>
        <h1>NBES</h1>
        <button onClick={logout} className="btn-secondary">
          Sign out
        </button>
      </header>

      <main>
        <div className="card">
          <h2>Profile</h2>
          <table>
            <tbody>
              <tr><td>User ID</td><td><code>{user.sub}</code></td></tr>
              <tr><td>Email</td><td>{user.email || "—"}</td></tr>
              <tr><td>Name</td><td>{user.name || user.preferred_username || "—"}</td></tr>
            </tbody>
          </table>
        </div>

        {userinfo && (
          <div className="card">
            <h2>Userinfo (OIDC)</h2>
            <pre>{JSON.stringify(userinfo, null, 2)}</pre>
          </div>
        )}

        <div className="card">
          <h2>Authenticated</h2>
          <p>You are signed in to NBES.</p>
        </div>
      </main>
    </div>
  );
}
