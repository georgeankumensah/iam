import { UserManager } from "oidc-client-ts";
import type { User, UserManagerSettings, SignoutResponse } from "oidc-client-ts";
import { BroadcastService } from "./broadcast-channel";
import type { AuthEvent, AuthEventCallback } from "./types";

export class SharedAuthManager {
  private user_manager: UserManager;
  private broadcast: BroadcastService;
  private event_listeners: Map<string, Set<AuthEventCallback>> = new Map();
  private unsub_broadcast: () => void;

  constructor(settings: UserManagerSettings) {
    this.user_manager = new UserManager(settings);
    this.broadcast = new BroadcastService();

    this.unsub_broadcast = this.broadcast.subscribe((msg) => {
      switch (msg.type) {
        case "LOGOUT":
          this.emit({ type: "cross_tab_logout", user: null });
          this.user_manager.removeUser().catch(() => {});
          break;
        case "AUTH_STATE_CHANGED":
          if (msg.payload && typeof msg.payload === "object" && "profile" in msg.payload) {
            this.emit({ type: "cross_tab_auth", user: msg.payload as User });
          }
          break;
        case "SESSION_EXPIRED":
          this.emit({ type: "session_expired", user: null });
          break;
      }
    });

    this.user_manager.events.addUserLoaded((user: User) => {
      this.broadcast.send("AUTH_STATE_CHANGED", user);
      this.emit({ type: "user_loaded", user });
    });

    this.user_manager.events.addUserUnloaded(() => {
      this.emit({ type: "user_unloaded", user: null });
    });

    this.user_manager.events.addUserSignedOut(() => {
      this.broadcast.send("LOGOUT");
      this.emit({ type: "user_signed_out", user: null });
    });

    this.user_manager.events.addSilentRenewError(() => {
      this.broadcast.send("SESSION_EXPIRED");
    });

    this.user_manager.events.addAccessTokenExpired(() => {
      this.broadcast.send("SESSION_EXPIRED");
    });
  }

  async getUser(): Promise<User | null> {
    return this.user_manager.getUser();
  }

  async signinRedirect(extra_params?: Record<string, string>): Promise<void> {
    return this.user_manager.signinRedirect({ extraQueryParams: extra_params });
  }

  async signinCallback(url?: string): Promise<User> {
    const user = await this.user_manager.signinRedirectCallback(url);
    this.broadcast.send("AUTH_STATE_CHANGED", user);
    return user;
  }

  async signinSilent(): Promise<User | null> {
    try {
      const user = await this.user_manager.signinSilent();
      if (user) {
        this.broadcast.send("AUTH_STATE_CHANGED", user);
      }
      return user;
    } catch {
      return null;
    }
  }

  async signoutRedirect(): Promise<void> {
    this.broadcast.send("LOGOUT");
    return this.user_manager.signoutRedirect();
  }

  async signoutCallback(url?: string): Promise<void> {
    await this.user_manager.signoutRedirectCallback(url);
  }

  async removeUser(): Promise<void> {
    await this.user_manager.removeUser();
  }

  async revokeTokens(): Promise<void> {
    const user = await this.user_manager.getUser();
    if (user) {
      const types: ("access_token" | "refresh_token")[] = [];
      if (user.refresh_token) types.push("refresh_token");
      if (user.access_token) types.push("access_token");
      if (types.length > 0) {
        await this.user_manager.revokeTokens(types);
      }
    }
  }

  on(event: AuthEvent["type"], callback: AuthEventCallback): () => void {
    if (!this.event_listeners.has(event)) {
      this.event_listeners.set(event, new Set());
    }
    this.event_listeners.get(event)!.add(callback);
    return () => {
      this.event_listeners.get(event)?.delete(callback);
    };
  }

  get user_manager_internal(): UserManager {
    return this.user_manager;
  }

  destroy(): void {
    this.unsub_broadcast();
    this.broadcast.destroy();
    this.event_listeners.clear();
  }

  private emit(event: AuthEvent): void {
    const listeners = this.event_listeners.get(event.type);
    if (listeners) {
      listeners.forEach((fn) => fn(event));
    }
  }
}
