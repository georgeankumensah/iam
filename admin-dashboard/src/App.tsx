import { AuthProvider, useAuth } from "@zitadel/react-auth";
import type { ReactNode } from "react";
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

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) {
    return (
      <div className="login-page">
        <div className="card">
          <h1>Loading...</h1>
          <div className="spinner" />
        </div>
      </div>
    );
  }
  if (!isAuthenticated) {
    window.location.href = "/login";
    return null;
  }
  return <>{children}</>;
}

function route(): string {
  const { pathname } = window.location;
  if (pathname === "/login") return "login";
  if (pathname === "/logout" || pathname === "/logout/done") return "logout";
  return pathname;
}

export default function App() {
  return (
    <AuthProvider
      authority={ZITADEL_AUTHORITY}
      client_id={OIDC_CLIENT_ID}
      redirect_uri={OIDC_REDIRECT_URI}
      post_logout_redirect_uri={OIDC_POST_LOGOUT_URI}
      scope={OIDC_SCOPE}
      extraQueryParams={{ api_base: API_BASE }}
      monitorSession={true}
      automaticSilentRenew={true}
      onSigninCallback={() => {
        window.history.replaceState({}, document.title, window.location.pathname);
      }}
    >
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
