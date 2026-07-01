import { AuthProvider, hasAuthParams } from "@zitadel/react-auth";
import { WebStorageStateStore } from "oidc-client-ts";
import Login from "./pages/Login";
import Callback from "./pages/Callback";
import Home from "./pages/Home";

const AUTH = import.meta.env.VITE_OIDC_AUTHORITY as string;
const CID = import.meta.env.VITE_OIDC_CLIENT_ID as string;
const REDIR = import.meta.env.VITE_OIDC_REDIRECT_URI as string;
const LOGOUT = import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI as string;

function getRoute() {
  const { pathname } = window.location;
  if (pathname === "/login/callback") return "callback";
  if (pathname === "/login") return "login";
  return "home";
}

export default function App() {
  return (
    <AuthProvider
      authority={AUTH}
      client_id={CID}
      redirect_uri={REDIR}
      post_logout_redirect_uri={LOGOUT}
      monitorSession={true}
      automaticSilentRenew={true}
      userStore={new WebStorageStateStore({ store: window.localStorage })}
      onSigninCallback={() => {
        window.history.replaceState(
          {},
          document.title,
          window.location.pathname,
        );
        const returnTo = sessionStorage.getItem("return_to");
        if (returnTo) {
          sessionStorage.removeItem("return_to");
          window.location.href = returnTo;
        }
      }}
    >
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
