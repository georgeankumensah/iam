import { AuthProvider } from "@rfdtech/oidc-client/react";
import type { ZitadelConfigInput } from "@rfdtech/oidc-client";
import Login from "./pages/Login";
import Callback from "./pages/Callback";
import Home from "./pages/Home";

const config: ZitadelConfigInput = {
  authority: import.meta.env.VITE_OIDC_AUTHORITY as string,
  client_id: import.meta.env.VITE_OIDC_CLIENT_ID as string,
  redirect_uri: import.meta.env.VITE_OIDC_REDIRECT_URI as string,
  post_logout_redirect_uri: import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI as string,
};

function getRoute() {
  const { pathname } = window.location;
  if (pathname === "/login/callback") return "callback";
  if (pathname === "/login") return "login";
  return "home";
}

export default function App() {
  return (
    <AuthProvider config={config}>
      <Router />
    </AuthProvider>
  );
}

function Router() {
  const route = getRoute();
  switch (route) {
    case "login":
      return <Login />;
    case "callback":
      return <Callback />;
    case "home":
      return <Home />;
  }
}
