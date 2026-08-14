/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        display: ['"Syne"', '"DM Sans"', 'system-ui', 'sans-serif'],
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
          DEFAULT: 'rgb(var(--ry-surface) / <alpha-value>)',
          raised: 'rgb(var(--ry-raised) / <alpha-value>)',
          overlay: 'rgb(var(--ry-overlay) / <alpha-value>)',
          hover: 'rgb(var(--ry-hover) / <alpha-value>)',
        },
        brand: {
          DEFAULT: '#5b8def',
          light: '#8bb0f7',
          glow: 'rgba(91, 141, 239, 0.28)',
        },
        insurance: '#38bdf8',
        mortgage: '#a78bfa',
        lending: '#34d399',
      },
      boxShadow: {
        glow: 'var(--ry-glow)',
        card: 'var(--ry-card-shadow)',
      },
      backgroundImage: {
        mesh: 'var(--ry-mesh)',
        'hero-glow': 'var(--ry-hero)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out both',
        'slide-up': 'slideUp 0.55s ease-out both',
        'pulse-soft': 'pulseSoft 2.4s ease-in-out infinite',
        float: 'floatY 4.5s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(14px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        pulseSoft: { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.55 } },
        floatY: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-6px)' } },
      },
    },
  },
  plugins: [],
};
