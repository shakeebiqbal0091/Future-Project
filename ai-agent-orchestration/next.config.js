/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    formats: ['image/webp', 'image/avif'],
    contentDispositionType: 'attachment',
  },
  experimental: {
    appDir: true,
  },
}

module.exports = nextConfig