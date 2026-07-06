import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const STATIC_REDIRECTS: Record<string, string> = {
  "/dashboard": "/dashboard-pro",
  "/dashboard/diagnostics/new": "/dashboard-pro/new",
  "/dashboard/clients": "/dashboard-pro/clients",
  "/dashboard/reviews": "/dashboard-pro/reviews",
  "/dashboard/compliance": "/dashboard-pro/compliance",
  "/dashboard/ledger": "/dashboard-pro/evidence",
  "/dashboard/admin": "/dashboard-pro",
};

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const staticTarget = STATIC_REDIRECTS[pathname];
  if (staticTarget) {
    return NextResponse.redirect(new URL(staticTarget, request.url));
  }

  const diagnosticMatch = pathname.match(/^\/dashboard\/diagnostics\/([^/]+)$/);
  if (diagnosticMatch) {
    return NextResponse.redirect(
      new URL(`/dashboard-pro/cases/${diagnosticMatch[1]}`, request.url),
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard", "/dashboard/:path*"],
};
