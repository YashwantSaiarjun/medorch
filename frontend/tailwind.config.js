/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f7f4',
          100: '#e0ede8',
          200: '#c1dbd1',
          300: '#6BAF9E',
          400: '#4A7C6F',
          500: '#3a6358',
          600: '#2d4f46',
          700: '#1A2E2A',
        },
        surface: '#F8FAF9',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}