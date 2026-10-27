import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  // Generate a cryptographically secure random nonce per request
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
  const isDev = process.env.NODE_ENV !== 'production';

  // In production: strict-dynamic with nonce, strictly no unsafe-eval and no unsafe-inline for scripts.
  // In development: Next.js dev server hot-reloading requires unsafe-eval for scripts and unsafe-inline for dynamic CSS injection.
  const scriptSrc = isDev
    ? `'self' 'nonce-${nonce}' 'strict-dynamic' 'unsafe-eval'`
    : `'self' 'nonce-${nonce}' 'strict-dynamic'`;

  const styleSrc = isDev
    ? `'self' https://fonts.googleapis.com 'unsafe-inline'`
    : `'self' 'nonce-${nonce}' https://fonts.googleapis.com 'unsafe-inline'`;

  // Exact map tile hosts: OpenStreetMap tiles
  const mapTileHosts = 'https://*.tile.openstreetmap.org https://tile.openstreetmap.org';

  // Exact API origin: deployed Render backend and local dev API
  const connectSrc = "'self' https://utsav-ai-ycg2.onrender.com http://localhost:8000 http://127.0.0.1:8000";

  // Content Security Policy directive definition
  const cspHeader = [
    `default-src 'self'`,
    `script-src ${scriptSrc}`,
    `style-src ${styleSrc}`,
    `img-src 'self' data: blob: ${mapTileHosts}`,
    `font-src 'self' https://fonts.gstatic.com data:`,
    `connect-src ${connectSrc}`,
    `object-src 'none'`,
    `base-uri 'self'`,
    `form-action 'self'`,
    `frame-ancestors 'none'`,
  ].join('; ');

  // Clone request headers and set x-nonce so Server Components and Next.js internal script injector can read it
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);
  requestHeaders.set('Content-Security-Policy', cspHeader);

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // Attach Content-Security-Policy and standard security headers to HTTP response
  response.headers.set('Content-Security-Policy', cspHeader);
  response.headers.set('x-nonce', nonce);
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Permissions-Policy', 'geolocation=(self), camera=(), microphone=()');

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, icon.svg, robots.txt, sitemap.xml
     */
    {
      source: '/((?!_next/static|_next/image|favicon.ico|icon.svg|apple-touch-icon.png|favicon-.*\\.png).*)',
      missing: [
        { type: 'header', key: 'next-router-prefetch' },
        { type: 'header', key: 'purpose', value: 'prefetch' },
      ],
    },
  ],
};
