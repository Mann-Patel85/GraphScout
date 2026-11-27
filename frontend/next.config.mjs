/** @type {import('next').NextConfig} */
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // The /api rewrite proxy drops requests after 30s by default. Investigations take
    // 1-2 min on rate-limited LLM tiers and benchmarks far longer, so allow 15 min.
    proxyTimeout: 15 * 60 * 1000,
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
      // FastAPI's interactive docs (the docs page fetches /openapi.json)
      { source: "/docs", destination: `${BACKEND_URL}/docs` },
      { source: "/openapi.json", destination: `${BACKEND_URL}/openapi.json` },
    ];
  },
};

export default nextConfig;
