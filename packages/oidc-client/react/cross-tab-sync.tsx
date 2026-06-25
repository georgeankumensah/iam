import { useEffect, useRef } from "react";
import { useAuth } from "react-oidc-context";
import { BroadcastService } from "../src/broadcast-channel";

export function CrossTabSync() {
  const auth = useAuth();
  const broadcastRef = useRef<BroadcastService | null>(null);

  useEffect(() => {
    const broadcast = new BroadcastService();
    broadcastRef.current = broadcast;

    const unsubBroadcast = broadcast.subscribe((msg) => {
      switch (msg.type) {
        case "LOGOUT":
          void auth.signoutRedirect();
          break;
        case "SESSION_EXPIRED":
          void auth.removeUser();
          break;
      }
    });

    const unsubLoaded = auth.events?.addUserLoaded(() => {
      broadcast.send("AUTH_STATE_CHANGED");
    });

    const unsubUnloaded = auth.events?.addUserUnloaded(() => {
      broadcast.send("AUTH_STATE_CHANGED");
    });

    const unsubSignedOut = auth.events?.addUserSignedOut(() => {
      broadcast.send("LOGOUT");
    });

    const unsubTokenExpired = auth.events?.addAccessTokenExpired(() => {
      broadcast.send("SESSION_EXPIRED");
    });

    const unsubSilentRenewError = auth.events?.addSilentRenewError(() => {
      broadcast.send("SESSION_EXPIRED");
    });

    return () => {
      unsubBroadcast();
      unsubLoaded?.();
      unsubUnloaded?.();
      unsubSignedOut?.();
      unsubTokenExpired?.();
      unsubSilentRenewError?.();
      broadcast.destroy();
    };
  }, []);

  return null;
}
