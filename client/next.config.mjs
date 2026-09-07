/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: { remotePatterns: [{ protocol: "https", hostname: "**.dzcdn.net" },
                             { protocol: "https", hostname: "i.ytimg.com" }] },
};
export default nextConfig;
