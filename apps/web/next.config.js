/** @type {import('next').NextConfig} */
const apiBackend = process.env.API_BACKEND_URL || 'http://127.0.0.1:8000';
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: '/api/v1/:path*', destination: `${apiBackend}/v1/:path*` },
      { source: '/api/:path*', destination: `${apiBackend}/api/:path*` },
    ];
  },
};

module.exports = nextConfig;
