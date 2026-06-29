import { useEffect, useState } from "react";
import { hasAuthParams, useAuth } from "@zitadel/react-auth";

export default function Home() {
  const { user, isAuthenticated, isLoading, signoutRedirect } = useAuth();
  const access_token = user?.access_token ?? null;
  const [userinfo, setUserinfo] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated && !hasAuthParams()) {
      sessionStorage.setItem("return_to", window.location.pathname);
      window.location.href = "/login";
      return;
    }

    if (!access_token) return;

    fetch(`${import.meta.env.VITE_OIDC_AUTHORITY}/oidc/v1/userinfo`, {
      headers: { Authorization: `Bearer ${access_token}` },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then(setUserinfo)
      .catch(() => setUserinfo(null));
  }, [isAuthenticated, isLoading, access_token]);

  const userRoles: string[] = (() => {
    const profile = user?.profile as Record<string, unknown> | undefined;
    if (!profile) return [];
    const roles: string[] = [];
    for (const [key, val] of Object.entries(profile)) {
      if (key.startsWith("urn:zitadel:iam:org:project") && key.endsWith(":roles") && val && typeof val === "object") {
        roles.push(...Object.keys(val as Record<string, unknown>));
      }
    }
    return roles.sort();
  })();

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
        <h1>Application Management System</h1>
        <button onClick={signoutRedirect} className="btn-secondary">
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
              <tr><td>Roles</td><td>{userRoles.length > 0 ? userRoles.join(", ") : "—"}</td></tr>
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
          <h2>Token Info</h2>
          <p>You are authenticated. Use the access token in API requests.</p>
        </div>
      </main>
    </div>
  );
}
