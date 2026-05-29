import { NextResponse } from 'next/server';

export function middleware(request: Request) {
  const response = NextResponse.next();
  response.headers.set('x-content-type-options', 'nosniff');
  response.headers.set('x-frame-options', 'DENY');
  response.headers.set('strict-transport-security', 'max-age=31536000; includeSubDomains');
  return response;
}

export const config = {
  matcher: '/:path*',
};