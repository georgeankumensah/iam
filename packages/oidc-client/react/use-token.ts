import { useState, useEffect, useCallback } from "react";
import type { User } from "oidc-client-ts";
import { useAuth } from "./use-auth";

export interface UseTokenResult {
  access_token: string | null;
  refresh: () => Promise<string | undefined>;
  is_expired: boolean;
  expires_at: number | null;
}

function isTokenExpired(user: User | null): boolean {
  if (!user?.expires_at) return true;
  return Date.now() / 1000 >= user.expires_at;
}

export function useToken(): UseTokenResult {
  const { user, get_access_token } = useAuth();
  const [access_token, setAccessToken] = useState<string | null>(() =>
    user?.access_token ?? null,
  );
  const [is_expired, setIsExpired] = useState(() => isTokenExpired(user));

  useEffect(() => {
    setAccessToken(user?.access_token ?? null);
    setIsExpired(isTokenExpired(user));
  }, [user]);

  const refresh = useCallback(async () => {
    const token = await get_access_token();
    setAccessToken(token ?? null);
    setIsExpired(false);
    return token;
  }, [get_access_token]);

  return {
    access_token,
    refresh,
    is_expired,
    expires_at: user?.expires_at ?? null,
  };
}
