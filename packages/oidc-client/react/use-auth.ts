import { useAuth as useOidcAuth } from "react-oidc-context";

export interface UseAuthResult {
  user: import("oidc-client-ts").User | null;
  is_authenticated: boolean;
  is_loading: boolean;
  error: Error | null;
  login: (extra_params?: Record<string, string>) => Promise<void>;
  logout: () => Promise<void>;
  get_access_token: () => Promise<string | undefined>;
}

export function useAuth(): UseAuthResult {
  const oidc = useOidcAuth();

  return {
    user: oidc.user ?? null,
    is_authenticated: oidc.isAuthenticated,
    is_loading: oidc.isLoading,
    error: oidc.error ?? null,
    login: async (extra_params) => {
      await oidc.signinRedirect({ extraQueryParams: extra_params });
    },
    logout: async () => {
      try {
        await oidc.revokeTokens();
      } catch {
        // Best-effort token revocation
      }
      await oidc.signoutRedirect();
    },
    get_access_token: async () => {
      return oidc.user?.access_token;
    },
  };
}
