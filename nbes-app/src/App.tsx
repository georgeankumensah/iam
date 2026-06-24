import { AuthProvider } from "@clet/oidc-client/react";
import type { ZitadelConfigInput } from "@clet/oidc-client";
import Login from "./pages/Login";
import Callback from "./pages/Callback";
import Home from "./pages/Home";

const config: ZitadelConfigInput = {
  authority: "http://localhost:3000",
  client_id: "378842413810057220",
  redirect_uri: "http://localhost:5174/login/callback",
  post_logout_redirect_uri: "http://localhost:5174/login?silent=false",
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
