import type { User, UserManagerSettings } from "oidc-client-ts";

export type AuthMessageType =
  | "AUTH_STATE_CHANGED"
  | "LOGOUT"
  | "TOKEN_REFRESHED"
  | "SESSION_EXPIRED"
  | "PING"
  | "PONG";

export interface AuthMessage {
  type: AuthMessageType;
  payload?: unknown;
  tabId: string;
  timestamp: number;
}

export interface ZitadelConfigInput {
  authority: string;
  client_id: string;
  redirect_uri: string;
  post_logout_redirect_uri?: string;
  scope?: string;
  silent_redirect_uri?: string;
  monitor_session?: boolean;
  automatic_silent_renew?: boolean;
  extra_query_params?: Record<string, string>;
}

export interface AuthState {
  user: User | null;
  is_authenticated: boolean;
  is_loading: boolean;
  error: Error | null;
}

export type AuthEventCallback = (event: AuthEvent) => void;

export interface AuthEvent {
  type: "user_loaded" | "user_unloaded" | "user_signed_out" | "token_refreshed" | "session_expired" | "cross_tab_logout" | "cross_tab_auth";
  user: User | null;
}

export type { User, UserManagerSettings };
