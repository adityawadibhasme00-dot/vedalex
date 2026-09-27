/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // In Docker Compose, SSR-side calls must reach the backend service by
    // its container hostname (http://backend:8000) rather than localhost.
    // BACKEND_URL is set to "http://backend:8000" in docker-compose.yml;
    // locally it defaults to http://localhost:8000.
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;