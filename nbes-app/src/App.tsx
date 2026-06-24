import Login from "./pages/Login";
import Callback from "./pages/Callback";
import Home from "./pages/Home";

function getRoute() {
  const { pathname, search } = window.location;
  if (pathname === "/login/callback") return "callback";
  if (pathname === "/login") return "login";
  return "home";
}

export default function App() {
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
