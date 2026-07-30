/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        display: ['"Cal Sans"', '"Inter"', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Brighter muted greys — default slate-400/500 washed out on dark surfaces
        slate: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#d0dae8',
          400: '#b4c2d6',
          500: '#8fa3bc',
          600: '#6b7f99',
          700: '#526378',
          800: '#3a4658',
          900: '#1e293b',
          950: '#0f172a',
        },
        surface: {
          DEFAULT: '#10141f',
          raised: '#161d2c',
          overlay: '#1c2538',
          hover: '#243044',
        },
        brand: {
          DEFAULT: '#5b8def',
          light: '#8bb0f7',
          glow: 'rgba(91, 141, 239, 0.28)',
        },
        insurance: '#38bdf8',
        mortgage: '#a78bfa',
      },
      boxShadow: {
        glow: '0 0 40px rgba(91, 141, 239, 0.15)',
        card: '0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 32px rgba(0,0,0,0.4)',
      },
      backgroundImage: {
        mesh: 'radial-gradient(at 20% 20%, rgba(91,141,239,0.18) 0, transparent 50%), radial-gradient(at 80% 0%, rgba(167,139,250,0.12) 0, transparent 45%), radial-gradient(at 50% 100%, rgba(56,189,248,0.08) 0, transparent 50%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        pulseSoft: { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.5 } },
      },
    },
  },
  plugins: [],
};
