/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{vue,js,ts}"],
  theme: {
    extend: {
      colors: {
        "indb-black": "#0a0a0a",
        "indb-red": "#e63329",
        "indb-white": "#f5f0e8",
        "indb-grey": "#1a1a1a",
        "indb-grey-light": "#2a2a2a",
        "indb-yellow": "#f6e05e",
        "indb-muted": "#8a8580",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
