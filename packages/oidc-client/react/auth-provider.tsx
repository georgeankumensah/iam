import { useEffect, type ReactNode } from "react";
import { AuthProvider as OidcAuthProvider, useAuth } from "react-oidc-context";
import { createZitadelConfig } from "../src/zitadel-config";
import type { ZitadelConfigInput } from "../src/types";
import { CrossTabSync } from "./cross-tab-sync";

export interface AuthProviderProps {
  config: ZitadelConfigInput;
  children: ReactNode;
  on_error?: (error: Error) => void;
}

function ErrorReporter({ on_error }: { on_error?: (error: Error) => void }) {
  const { error } = useAuth();
  useEffect(() => {
    if (error && on_error) {
      on_error(error instanceof Error ? error : new Error(String(error)));
    }
  }, [error]);
  return null;
}

export function AuthProvider({ config, children, on_error }: AuthProviderProps) {
  const settings = createZitadelConfig(config);

  return (
    <OidcAuthProvider
      {...settings}
      onSigninCallback={() => {
        window.history.replaceState({}, document.title, window.location.pathname);
      }}
    >
      <ErrorReporter on_error={on_error} />
      <CrossTabSync />
      {children}
    </OidcAuthProvider>
  );
}
