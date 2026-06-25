import { useEffect, useState, useRef, useCallback, type ReactNode } from "react";
import { SharedAuthManager } from "../src/shared-auth-manager";
import { createZitadelConfig } from "../src/zitadel-config";
import type { User } from "oidc-client-ts";
import type { ZitadelConfigInput } from "../src/types";
import { AuthContext } from "./auth-context";
import type { AuthContextValue } from "./auth-context";

export interface AuthProviderProps {
  config: ZitadelConfigInput;
  children: ReactNode;
  on_error?: (error: Error) => void;
}

export function AuthProvider({ config, children, on_error }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [is_loading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const manager_ref = useRef<SharedAuthManager | null>(null);

  useEffect(() => {
    const settings = createZitadelConfig(config);
    const manager = new SharedAuthManager(settings);
    manager_ref.current = manager;

    const unsubs = [
      manager.on("user_loaded", (ev) => {
        setUser(ev.user);
        setIsLoading(false);
        setError(null);
      }),
      manager.on("user_unloaded", () => {
        setUser(null);
      }),
      manager.on("user_signed_out", () => {
        setUser(null);
      }),
      manager.on("cross_tab_logout", () => {
        setUser(null);
      }),
      manager.on("session_expired", () => {
        setUser(null);
      }),
      manager.on("cross_tab_auth", (ev) => {
        setUser(ev.user);
        setIsLoading(false);
      }),
    ];

    async function init() {
      try {
        const search_params = new URLSearchParams(window.location.search);
        const has_auth_params = search_params.has("code") && search_params.has("state");

        if (has_auth_params) {
          const callback_url = window.location.href;
          const clean_url = window.location.origin + window.location.pathname;
          window.history.replaceState({}, "", clean_url);
          const u = await manager.signinCallback(callback_url);
          setUser(u);
        } else {
          const u = await manager.getUser();
          setUser(u);
        }
      } catch (err) {
        const e = err instanceof Error ? err : new Error(String(err));
        setError(e);
        on_error?.(e);
      } finally {
        setIsLoading(false);
      }
    }

    void init();

    return () => {
      unsubs.forEach((u) => u());
      manager.destroy();
      manager_ref.current = null;
    };
  }, []);

  const login = useCallback(async (extra_params?: Record<string, string>) => {
    const mgr = manager_ref.current;
    if (!mgr) return;
    await mgr.signinRedirect(extra_params);
  }, []);

  const logout = useCallback(async () => {
    const mgr = manager_ref.current;
    if (!mgr) return;
    try {
      await mgr.revokeTokens();
    } catch {
      // Best-effort token revocation
    }
    await mgr.signoutRedirect();
  }, []);

  const get_access_token = useCallback(async (): Promise<string | undefined> => {
    const mgr = manager_ref.current;
    if (!mgr) return undefined;
    const u = await mgr.getUser();
    if (!u || u.expired) return undefined;
    return u.access_token;
  }, []);

  const value: AuthContextValue = {
    state: {
      user,
      is_authenticated: user !== null && !user.expired,
      is_loading,
      error,
    },
    login,
    logout,
    get_access_token,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
