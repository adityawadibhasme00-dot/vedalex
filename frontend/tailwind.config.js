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
        // Public-portal palette: the flat, high-contrast grammar used by
        // Indian government websites. No gradients, no glass, 1px rules.
        gov: {
          navy:   '#0a1f44',  // utility strip
          blue:   '#0d3b8f',  // primary navigation bar
          blueDk: '#082a66',
          link:   '#0b4a9e',
          saffron:'#ff9933',
          green:  '#138808',
          rule:   '#d4d7dd',  // hairline borders
          wash:   '#f2f5f9',  // banded section background
          ink:    '#1b1f24',
          mute:   '#5b6472',
        },
        // Neutral government-gray scale (no blue undertone). Every
        // text-slate-* and text-gray-* resolves to this, matching portal
        // body copy hues exactly.
        slate: {
          50:  '#f2f5f9',
          100: '#e8ecf1',
          200: '#d9dee5',
          300: '#b7bdc6',
          400: '#8a93a1',
          500: '#6b7482',
          600: '#5b6472',
          700: '#424a56',
          800: '#2c333c',
          900: '#1b1f24',
        },
        gray: {
          50:  '#f2f5f9',
          100: '#e8ecf1',
          200: '#d9dee5',
          300: '#b7bdc6',
          400: '#8a93a1',
          500: '#6b7482',
          600: '#5b6472',
          700: '#424a56',
          800: '#2c333c',
          900: '#1b1f24',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Lora', 'Georgia', 'serif'],
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