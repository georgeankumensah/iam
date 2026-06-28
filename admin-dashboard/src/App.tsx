import { AuthProvider, ProtectedRoute } from "@rfdtech/oidc-client/react";
import type { ZitadelConfigInput } from "@rfdtech/oidc-client";
import {
  API_BASE,
  OIDC_CLIENT_ID,
  OIDC_POST_LOGOUT_URI,
  OIDC_REDIRECT_URI,
  OIDC_SCOPE,
  ZITADEL_AUTHORITY,
} from "./lib/env";
import { Dashboard } from "./pages/Dashboard";
import { Users } from "./pages/Users";
import { Login } from "./pages/Login";
import { LogoutDone } from "./pages/LogoutDone";

const config: ZitadelConfigInput = {
  authority: ZITADEL_AUTHORITY,
  client_id: OIDC_CLIENT_ID,
  redirect_uri: OIDC_REDIRECT_URI,
  post_logout_redirect_uri: OIDC_POST_LOGOUT_URI,
  scope: OIDC_SCOPE,
  monitor_session: false,
  automatic_silent_renew: false,
  extra_query_params: { api_base: API_BASE },
};

function route(): string {
  const { pathname } = window.location;
  if (pathname === "/login") return "login";
  if (pathname === "/logout" || pathname === "/logout/done") return "logout";
  return pathname;
}

export default function App() {
  return (
    <AuthProvider config={config}>
      <Router />
    </AuthProvider>
  );
}

function Router() {
  const r = route();
  switch (r) {
    case "login":
      return <Login />;
    case "logout":
      return <LogoutDone />;
    case "/users":
      return (
        <ProtectedRoute>
          <Users />
        </ProtectedRoute>
      );
    default:
      return (
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      );
  }
}
