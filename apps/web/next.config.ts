/** @type {import('next').NextConfig} */

/** Normalize API base for rewrites — Vercel rejects destinations without http(s):// */
function apiBaseUrl(): string {
  const raw = (process.env.NEXT_PUBLIC_API_URL ?? "").trim();
  if (!raw) return "http://localhost:8000";
  const withoutTrailingSlash = raw.replace(/\/+$/, "");
  if (withoutTrailingSlash.startsWith("http://") || withoutTrailingSlash.startsWith("https://")) {
    return withoutTrailingSlash;
  }
  return `https://${withoutTrailingSlash}`;
}

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/health",
        destination: `${apiBaseUrl()}/health`,
      },
    ];
  },
};

export default nextConfig;
