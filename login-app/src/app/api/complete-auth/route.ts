import { NextRequest, NextResponse } from "next/server";

const DJANGO_BASE_URL = process.env.IAM_API_URL || "http://django:8000";

export async function GET(request: NextRequest) {
  const authRequest = request.nextUrl.searchParams.get("authRequest");
  if (!authRequest) {
    return NextResponse.json({ error: "missing authRequest" }, { status: 400 });
  }

  const djangoUrl = `${DJANGO_BASE_URL}/login/complete?authRequest=${encodeURIComponent(authRequest)}`;

  try {
    const response = await fetch(djangoUrl, {
      headers: {
        Cookie: request.headers.get("cookie") || "",
      },
      redirect: "manual",
      signal: AbortSignal.timeout(15000),
    });

    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get("location");
      if (location) {
        return NextResponse.redirect(location);
      }
    }

    const text = await response.text();
    return NextResponse.redirect(
      new URL(`/error?error=oidc_completion_failed&detail=${encodeURIComponent(text.slice(0, 200))}`, request.url),
    );
  } catch {
    return NextResponse.redirect(
      new URL("/error?error=oidc_completion_failed", request.url),
    );
  }
}
