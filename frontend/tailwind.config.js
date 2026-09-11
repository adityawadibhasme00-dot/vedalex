/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg:    { main: '#0B1120', card: '#111827', elevated: '#1F2937' },
        brand: { blue: '#3B82F6', violet: '#8B5CF6', cyan: '#06B6D4' },
        semantic: {
          success: '#22C55E',
          warning: '#F59E0B',
          danger:  '#EF4444',
          info:    '#3B82F6',
        },
        ayur: {
          50:  '#ecfdf5', 100: '#d1fae5',
          500: '#10b981', 600: '#059669',
          700: '#047857', 800: '#065f46', 900: '#064e3b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Outfit', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.35)',
        'glass-lg': '0 16px 48px rgba(0, 0, 0, 0.45)',
        'glow-blue': '0 0 20px rgba(59,130,246,0.25)',
        'glow-violet': '0 0 20px rgba(139,92,246,0.25)',
        'glow-emerald': '0 0 20px rgba(16,185,129,0.25)',
      },
      keyframes: {
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'slide-up': 'slide-up 0.4s ease forwards',
      },
    },
  },
  plugins: [],
};