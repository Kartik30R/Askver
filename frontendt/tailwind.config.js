/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Core Brand
        nagarro: {
          green: '#47D7AC',   // The exact Nagarro primary green
          hover: '#36B894',   // Slightly darker for hover states
          active: '#2A9E7D',  // Even darker for click/active states
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