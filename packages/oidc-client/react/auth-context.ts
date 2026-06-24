import { createContext } from "react";
import type { User } from "oidc-client-ts";
import type { AuthState } from "../src/types";

export interface AuthContextValue {
  state: AuthState;
  login: (extra_params?: Record<string, string>) => Promise<void>;
  logout: () => Promise<void>;
  get_access_token: () => Promise<string | undefined>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
