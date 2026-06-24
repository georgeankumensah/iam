import { createLogger } from "../logger";

const logger = createLogger("security-settings");

export async function getIframeOrigins(
  _baseUrl: string,
  _instanceHost: string | null,
  _publicHost: string | null
): Promise<string[] | null> {
  try {
    // In production, fetch from Zitadel API:
    // const resp = await fetch(`${baseUrl}/auth/v1/security`);
    // return resp.ok ? (await resp.json()).iframeOrigins : null;
    return null;
  } catch (err) {
    logger.error("Failed to fetch iframe origins", {
      error: err instanceof Error ? err.message : String(err),
    });
    return null;
  }
}
