/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        display: ['"Source Serif 4"', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
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
          DEFAULT: '#C79A46',
          light: '#dcb15f',
          glow: 'rgba(199, 154, 70, 0.28)',
        },
        verdigris: {
          DEFAULT: '#3E8E82',
          soft: 'rgba(62, 142, 130, 0.14)',
        },
        risk: {
          red: '#C0524A',
          'red-soft': 'rgba(192, 82, 74, 0.14)',
          amber: '#C98A3A',
          'amber-soft': 'rgba(201, 138, 58, 0.14)',
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
