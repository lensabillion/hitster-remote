/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#0b0b14",
        accent: "#ff3d7f",
        accent2: "#7c5cff",
      },
      keyframes: {
        pop: {
          "0%": { transform: "scale(0.9)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        glow: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(255,61,127,0.4)" },
          "50%": { boxShadow: "0 0 40px rgba(124,92,255,0.6)" },
        },
      },
      animation: {
        pop: "pop 0.3s ease-out",
        glow: "glow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
