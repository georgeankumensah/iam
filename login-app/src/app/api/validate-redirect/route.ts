import { NextRequest, NextResponse } from "next/server";

const DJANGO_BASE_URL = process.env.IAM_DJANGO_BASE_URL || "http://localhost:8000";
const ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"];

export async function GET(request: NextRequest) {
  const uri = request.nextUrl.searchParams.get("uri");
  if (!uri) {
    return NextResponse.json({ valid: false });
  }

  // Relative paths are always OK.
  if (uri.startsWith("/")) {
    return NextResponse.json({ valid: true });
  }

  // Check static allowlist (fast path).
  try {
    const parsed = new URL(uri);
    if (ALLOWED_ORIGINS.includes(parsed.origin)) {
      return NextResponse.json({ valid: true });
    }
  } catch {
    return NextResponse.json({ valid: false });
  }

  // Fall back to Django DB-backed per-client validation.
  try {
    const resp = await fetch(
      `${DJANGO_BASE_URL}/v1/clients/validate-logout-redirect/?uri=${encodeURIComponent(uri)}`,
      { signal: AbortSignal.timeout(5000) },
    );
    const body = await resp.json();
    return NextResponse.json({ valid: body?.data?.valid ?? false });
  } catch {
    return NextResponse.json({ valid: false });
  }
}
