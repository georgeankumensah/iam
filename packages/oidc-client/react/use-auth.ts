import { useContext } from "react";
import type { User } from "oidc-client-ts";
import { AuthContext } from "./auth-context";

export interface UseAuthResult {
  user: User | null;
  is_authenticated: boolean;
  is_loading: boolean;
  error: Error | null;
  login: (extra_params?: Record<string, string>) => Promise<void>;
  logout: () => Promise<void>;
  get_access_token: () => Promise<string | undefined>;
}

export function useAuth(): UseAuthResult {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an <AuthProvider>");
  }

  return {
    user: ctx.state.user,
    is_authenticated: ctx.state.is_authenticated,
    is_loading: ctx.state.is_loading,
    error: ctx.state.error,
    login: ctx.login,
    logout: ctx.logout,
    get_access_token: ctx.get_access_token,
  };
}
