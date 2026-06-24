/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f5ff",
          100: "#e0ebff",
          200: "#b8d4fe",
          300: "#7cb4fc",
          400: "#4391f9",
          500: "#1a6ff5",
          600: "#0c52d5",
          700: "#0e41ac",
          800: "#12388b",
          900: "#153272",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
