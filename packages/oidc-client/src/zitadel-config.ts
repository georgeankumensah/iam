import type { UserManagerSettings } from "oidc-client-ts";
import { WebStorageStateStore } from "oidc-client-ts";
import type { ZitadelConfigInput } from "./types";

export function createZitadelConfig(input: ZitadelConfigInput): UserManagerSettings {
  return {
    authority: input.authority,
    client_id: input.client_id,
    redirect_uri: input.redirect_uri,
    post_logout_redirect_uri: input.post_logout_redirect_uri,
    response_type: "code",
    scope: input.scope ?? "openid profile email urn:zitadel:iam:org:project:roles",
    metadata: {
      issuer: input.authority,
      authorization_endpoint: `${input.authority}/oauth/v2/authorize`,
      token_endpoint: `${input.authority}/oauth/v2/token`,
      userinfo_endpoint: `${input.authority}/oidc/v1/userinfo`,
      end_session_endpoint: `${input.authority}/oidc/v1/end_session`,
      jwks_uri: `${input.authority}/oidc/v1/keys`,
      revocation_endpoint: `${input.authority}/oauth/v2/revoke`,
    },
    silent_redirect_uri: input.silent_redirect_uri,
    automaticSilentRenew: input.automatic_silent_renew ?? false,
    monitorSession: input.monitor_session ?? false,
    extraQueryParams: input.extra_query_params,
    userStore: new WebStorageStateStore({ store: localStorage }),
    filterProtocolClaims: true,
    loadUserInfo: true,
    revokeTokensOnSignout: true,
    revokeTokenTypes: ["access_token", "refresh_token"],
  } satisfies UserManagerSettings;
}
