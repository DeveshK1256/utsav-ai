/** @type {import('next').NextConfig} */
const isBuild = process.env.NODE_ENV === 'production';

const nextConfig = {
  ...(isBuild ? { output: 'export' } : {}),
  images: {
    unoptimized: true
  }
};

module.exports = nextConfig;
