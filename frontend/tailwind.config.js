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
        surface: {
          DEFAULT: '#0c0f17',
          raised: '#121826',
          overlay: '#181f2e',
          hover: '#1e2738',
        },
        brand: {
          DEFAULT: '#5b8def',
          light: '#7aa3f5',
          glow: 'rgba(91, 141, 239, 0.25)',
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
