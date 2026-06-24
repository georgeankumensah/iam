# @rfdtech/oidc-client

Shared OIDC auth state manager wrapping [oidc-client-ts](https://github.com/authts/oidc-client-ts) for RFD Tech IAM public clients. Adds cross-tab auth synchronization, React bindings, and Zitadel-aware defaults.

## Install

```bash
npm install @rfdtech/oidc-client oidc-client-ts react
```

Peer deps: `oidc-client-ts ^3.0`, `react ^18 || ^19`.

## Usage

### 1. Configure

```ts
import { createZitadelConfig } from "@rfdtech/oidc-client";

const config = createZitadelConfig({
  authority: "http://localhost:3000",       // OP base URL (login-app proxy)
  client_id: "your-client-id",
  redirect_uri: "http://localhost:5173/login/callback",
  post_logout_redirect_uri: "http://localhost:5173/login",
});
```

### 2. Wrap app

```tsx
import { AuthProvider } from "@rfdtech/oidc-client/react";

export default function App() {
  return (
    <AuthProvider config={config}>
      <Router />
    </AuthProvider>
  );
}
```

### 3. Use hooks

```tsx
import { useAuth, useToken } from "@rfdtech/oidc-client/react";

function Home() {
  const { user, is_authenticated, login, logout } = useAuth();
  const { access_token } = useToken();

  if (!is_authenticated) return <button onClick={login}>Sign in</button>;
  return <button onClick={logout}>Sign out ({user?.profile.email})</button>;
}
```

### 4. Protect routes

```tsx
import { ProtectedRoute } from "@rfdtech/oidc-client/react";

<ProtectedRoute fallback="/login">
  <Dashboard />
</ProtectedRoute>
```

## API

### Core (`@rfdtech/oidc-client`)

| Export | Description |
|---|---|
| `createZitadelConfig(input)` | Returns `UserManagerSettings` with Zitadel proxy endpoints |
| `SharedAuthManager` | Wraps oidc-client-ts `UserManager` with cross-tab sync |
| `BroadcastService` | BroadcastChannel message bus (`clet:oidc:auth` channel) |

### React (`@rfdtech/oidc-client/react`)

#### `AuthProvider`
**Props:**
| Prop | Type | Description |
|---|---|---|
| `config` | `ZitadelConfigInput` | OIDC configuration |
| `on_error?` | `(error: Error) => void` | Error callback |
| `children` | `ReactNode` | Component tree |

#### `useAuth()`
| Return | Type | Description |
|---|---|---|
| `user` | `User \| null` | oidc-client-ts User object |
| `is_authenticated` | `boolean` | `user !== null && !user.expired` |
| `is_loading` | `boolean` | Initialization in progress |
| `error` | `Error \| null` | Auth error |
| `login` | `(extra_params?) => Promise<void>` | Redirect to OP |
| `logout` | `() => Promise<void>` | Revoke tokens + RP-initiated logout |
| `get_access_token` | `() => Promise<string \| undefined>` | Current access token |

#### `useToken()`
| Return | Type | Description |
|---|---|---|
| `access_token` | `string \| null` | Current access token |
| `is_expired` | `boolean` | Token expired |
| `refresh` | `() => Promise<string \| undefined>` | Re-fetch from storage |
| `expires_at` | `number \| null` | Unix epoch expiry |

#### `ProtectedRoute`
| Prop | Type | Default | Description |
|---|---|---|---|
| `children` | `ReactNode` | — | Protected content |
| `fallback` | `string` | `"/login"` | Redirect target |

### `ZitadelConfigInput`

| Field | Type | Default | Description |
|---|---|---|---|
| `authority` | `string` | — | OP base URL |
| `client_id` | `string` | — | OIDC client ID |
| `redirect_uri` | `string` | — | Callback URL |
| `post_logout_redirect_uri?` | `string` | — | Post-logout redirect |
| `scope?` | `string` | `"openid profile email urn:zitadel:iam:org:project:roles"` | OIDC scopes |
| `silent_redirect_uri?` | `string` | — | Iframe callback for auto-renew |
| `monitor_session?` | `boolean` | `false` | Enable OP session polling |
| `automatic_silent_renew?` | `boolean` | `false` | Enable iframe token refresh |
| `extra_query_params?` | `Record<string, string>` | — | Extra authorize params |

## Cross-tab behavior

Auth state is synchronized across tabs via `BroadcastChannel`:

| Event | Direction | Effect |
|---|---|---|
| Login | All tabs | `user` updated, login page auto-redirects |
| Logout | All tabs | `removeUser()`, redirect to login |
| Token expired | Current tab | `user` set to null |

User tokens are stored in `localStorage` (shared across tabs) while OIDC protocol state (PKCE verifier) remains in `sessionStorage`.

## Changelog

### 0.1.0 (2026-06-24)

- Initial release
- `SharedAuthManager` with cross-tab BroadcastChannel sync
- `createZitadelConfig` with Zitadel proxy metadata
- React bindings: `AuthProvider`, `useAuth`, `useToken`, `ProtectedRoute`
- Token revocation on signout
- localStorage-backed user store
- Zitadel OIDC scopes and claim defaults
