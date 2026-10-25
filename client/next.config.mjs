/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Dev only. A second player on the same machine needs a second origin, since
  // the player id lives in localStorage; 127.0.0.1 is the one that costs nothing.
  allowedDevOrigins: ["127.0.0.1"],
};
export default nextConfig;
