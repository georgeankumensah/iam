interface HeaderActions {
  set: (key: string, value: string) => void;
  remove: (key: string) => void;
}

export function applyCustomHeaders(actions: HeaderActions): void {
  const customHeaders = process.env.CUSTOM_REQUEST_HEADERS;
  if (!customHeaders) return;

  for (const entry of customHeaders.split(",")) {
    const [action, key, ...rest] = entry.trim().split(" ");
    const value = rest.join(" ");
    if (action === "set" && key && value) {
      actions.set(key, value);
    } else if (action === "remove" && key) {
      actions.remove(key);
    }
  }
}
