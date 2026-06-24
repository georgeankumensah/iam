const PREFIX = "[iam-login]";

export function createLogger(name: string) {
  return {
    info: (message: string, meta?: Record<string, unknown>) =>
      console.log(`${PREFIX} [${name}] INFO: ${message}`, meta ?? ""),
    warn: (message: string, meta?: Record<string, unknown>) =>
      console.warn(`${PREFIX} [${name}] WARN: ${message}`, meta ?? ""),
    error: (message: string, meta?: Record<string, unknown>) =>
      console.error(`${PREFIX} [${name}] ERROR: ${message}`, meta ?? ""),
    debug: (message: string, meta?: Record<string, unknown>) =>
      console.debug(`${PREFIX} [${name}] DEBUG: ${message}`, meta ?? ""),
  };
}
