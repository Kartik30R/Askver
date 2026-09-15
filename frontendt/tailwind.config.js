/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Enforces dark mode styling
  theme: {
    extend: {
      colors: {
        // Core Brand
        nagarro: {
          green: '#B2D235',
          hover: '#9CBA2E',
          active: '#849C27',
        },
        // Cosmic Dark Theme
        cosmic: {
          bg: '#050B14',      // Deep space background
          surface: '#0B1221', // Slightly raised card surfaces
          glass: 'rgba(11, 18, 33, 0.65)', // For glassmorphism panels
          border: '#1F2937',  // Subtle borders for widgets
          text: '#F3F4F6',    // High contrast white text
          muted: '#9CA3AF'    // Secondary text for less important data
        }
      }
    },
  },
  plugins: [],
}