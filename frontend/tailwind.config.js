/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gold: {
          DEFAULT: '#C9A84C',
          bright: '#FFD700',
          dim: '#8B6914',
          light: '#E8C97A',
        },
        silver: {
          DEFAULT: '#C0C0C0',
          dark: '#808080',
          light: '#E8E8E8',
        },
        aurum: {
          bg: '#0a0a0a',
          card: '#111111',
          'card-border': 'rgba(201,168,76,0.2)',
          surface: '#161616',
        },
      },
      fontFamily: {
        cinzel: ['Cinzel', 'serif'],
        cormorant: ['Cormorant Garamond', 'serif'],
        raleway: ['Raleway', 'sans-serif'],
      },
      animation: {
        'shimmer': 'shimmer 2.5s ease-in-out infinite',
        'pulse-gold': 'pulse-gold 2s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'spin-slow': 'spin 8s linear infinite',
        'border-trace': 'border-trace 1s ease-in-out forwards',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        'pulse-gold': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(201,168,76,0.4)' },
          '50%': { boxShadow: '0 0 0 12px rgba(201,168,76,0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        'border-trace': {
          '0%': { strokeDashoffset: '100%' },
          '100%': { strokeDashoffset: '0%' },
        },
      },
      backgroundImage: {
        'gold-gradient': 'linear-gradient(135deg, #C9A84C 0%, #FFD700 50%, #C9A84C 100%)',
        'gold-shimmer': 'linear-gradient(90deg, #C9A84C 0%, #FFD700 25%, #E8C97A 50%, #FFD700 75%, #C9A84C 100%)',
        'dark-gradient': 'linear-gradient(180deg, #0a0a0a 0%, #111111 100%)',
      },
    },
  },
  plugins: [],
}
