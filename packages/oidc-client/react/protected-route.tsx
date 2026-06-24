import type { ReactNode } from "react";
import { useAuth } from "./use-auth";

export interface ProtectedRouteProps {
  children: ReactNode;
  fallback?: string;
}

export function ProtectedRoute({ children, fallback = "/login" }: ProtectedRouteProps) {
  const { is_authenticated, is_loading } = useAuth();

  if (is_loading) {
    return (
      <div className="login-page">
        <div className="card">
          <h1>Loading...</h1>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  if (!is_authenticated) {
    window.location.href = fallback;
    return null;
  }

  return <>{children}</>;
}
