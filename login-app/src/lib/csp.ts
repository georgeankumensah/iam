interface CSPOptions {
  serviceUrl: string;
  iframeOrigins?: string[];
}

export function buildCSP({ serviceUrl, iframeOrigins }: CSPOptions): string {
  const directives: string[] = [
    `default-src 'self' ${serviceUrl}`,
    `script-src 'self' 'unsafe-eval' 'unsafe-inline'`,
    `style-src 'self' 'unsafe-inline'`,
    `img-src 'self' data: blob: ${serviceUrl}`,
    `font-src 'self' data:`,
    `connect-src 'self' ${serviceUrl} blob:`,
    `frame-src 'self' ${iframeOrigins?.length ? iframeOrigins.join(" ") : "'none'"}`,
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ];

  return directives.join("; ");
}
