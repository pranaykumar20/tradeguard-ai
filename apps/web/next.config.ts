/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/health",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health`,
      },
    ];
  },
};

export default nextConfig;
