/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    outputFileTracingIncludes: {
      "/api/templates": ["./public/circuit-templates/**/*"],
      "/api/templates/route": ["./public/circuit-templates/**/*"],
    },
  },
};

module.exports = nextConfig;
