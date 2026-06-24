export interface ServiceConfig {
  baseUrl: string;
  publicHost: string | null;
  instanceHost: string | null;
}

export function getServiceConfig(headers?: Headers): { serviceConfig: ServiceConfig } {
  const apiUrl = process.env.ZITADEL_API_URL || "http://localhost:8080";
  const publicHost = headers?.get("x-zitadel-public-host") || process.env.ZITADEL_PUBLIC_HOST || null;
  const instanceHost = headers?.get("x-zitadel-instance-host") || null;

  return {
    serviceConfig: {
      baseUrl: apiUrl.replace(/\/$/, ""),
      publicHost,
      instanceHost,
    },
  };
}
