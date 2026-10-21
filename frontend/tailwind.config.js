/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        marigold: '#E67E22',
        kumkum: '#8B1E28',
        haldi: '#F4B41A',
        chandan: '#FAF7F2',
        chandanDark: '#0C0F14',
        surfaceDark: '#141820',
        borderDark: '#242C3A'
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['Playfair Display', 'serif'],
        devanagari: ['Rozha One', 'serif']
      }
    },
  },
  plugins: [],
}
