/** @type {import('next').NextConfig} */
// In standalone mode/Docker, we might read from process.env at runtime if we are careful,
// but usually Next.js bakes config.
// For rewrites, it uses the env var available at build time unless we use a custom server or middleware.
// However, Railway injects env vars at runtime.
// 'output: standalone' creates a server.js that respects process.env at runtime for port/hostname,
// but rewrites baked in next.config.js are often static.
// To support dynamic backend URL, we should ideally use middleware.
// But for now, let's assume we build with a placeholder or the env var is set before start (which Railway does).
const apiBackend = process.env.API_BACKEND_URL || 'https://robot-simulation-environment-production.up.railway.app';

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // Ensure we can access this in the browser if needed (though rewrites handle the proxy)
  env: {
    NEXT_PUBLIC_API_URL: apiBackend,
  },
  async rewrites() {
    return [
      // Important: Railway might provide the backend URL dynamically.
      // If we use 'standalone', server.js might pick up the new env var if we don't hardcode it here?
      // Actually, next.config.js is evaluated at server start in standalone mode.
      { source: '/api/v1/:path*', destination: `${apiBackend}/v1/:path*` },
      { source: '/api/:path*', destination: `${apiBackend}/api/:path*` },
    ];
  },
};

module.exports = nextConfig;
