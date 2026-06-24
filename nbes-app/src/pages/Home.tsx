import { useEffect, useState } from "react";
import { useAuth, useToken } from "@clet/oidc-client/react";

export default function Home() {
  const { user, is_authenticated, is_loading, logout } = useAuth();
  const { access_token } = useToken();
  const [userinfo, setUserinfo] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (is_loading) return;

    if (!is_authenticated) {
      window.location.href = "/login";
      return;
    }

    if (!access_token) return;

    fetch("http://localhost:3000/oidc/v1/userinfo", {
      headers: { Authorization: `Bearer ${access_token}` },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then(setUserinfo)
      .catch(() => setUserinfo(null));
  }, [is_authenticated, is_loading, access_token]);

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
              <tr><td>User ID</td><td><code>{user.profile.sub}</code></td></tr>
              <tr><td>Email</td><td>{user.profile.email || "—"}</td></tr>
              <tr><td>Name</td><td>{user.profile.name || user.profile.preferred_username || "—"}</td></tr>
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
