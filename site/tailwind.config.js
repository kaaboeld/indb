/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './components/**/*.{vue,js,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './app.vue',
  ],
  theme: {
    extend: {
      colors: {
        'indb-black': '#0a0a0a',
        'indb-red': '#E53E3E',
        'indb-white': '#f5f0e8',
        'indb-grey': '#1a1a1a',
        'indb-yellow': '#F6E05E',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
