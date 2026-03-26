export default {
  content: ["./index.html","./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg:      { primary: "#0a0f1a", secondary: "#0d1421", card: "#111827" },
        brand:   { green: "#00C896", red: "#FF4D6A", amber: "#F5A623", blue: "#3B82F6", purple: "#8B5CF6" },
      },
      fontFamily: { mono: ["Space Mono","monospace"], sans: ["DM Sans","sans-serif"] }
    }
  },
  plugins: []
}
