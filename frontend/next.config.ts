import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // Docker için önemli!

  // API proxy (development için backend'e yönlendir)
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://backend:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
