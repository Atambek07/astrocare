/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three'],
  // Separate QA builds from a running dev server to avoid shared .next corruption.
  distDir: process.env.NEXT_DIST_DIR || '.next',
};

export default nextConfig;
