/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#0A0F1C",
        panel: "rgba(17, 24, 39, 0.65)",
        neon: "#00E5FF",
        plasma: "#7C4DFF",
        success: "#00FF95",
        warning: "#FFB300",
        danger: "#FF3D71",
        textMain: "#E5F7FF",
        textWeak: "#8FA3BF"
      },
      boxShadow: {
        neon: "0 0 28px rgba(0, 229, 255, 0.28)",
        plasma: "0 0 30px rgba(124, 77, 255, 0.24)",
        danger: "0 0 28px rgba(255, 61, 113, 0.22)"
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        scan: "scan 3.5s linear infinite",
        pulseGlow: "pulseGlow 2.4s ease-in-out infinite"
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" }
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" }
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 18px rgba(0, 229, 255, 0.22)" },
          "50%": { boxShadow: "0 0 34px rgba(124, 77, 255, 0.34)" }
        }
      }
    }
  },
  plugins: []
};
