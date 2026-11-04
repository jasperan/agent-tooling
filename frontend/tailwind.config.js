/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter Tight', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace']
      },
      colors: {
        // One graphite ramp, tinted a half step cool, plus one signal amber.
        background: '#0F1115',
        surface: '#15181D',
        surface_alt: '#1C2027',
        surface_hover: '#20252D',
        line: 'rgba(255, 255, 255, 0.08)',
        line_strong: 'rgba(255, 255, 255, 0.16)',
        primary: '#D9A441',
        primary_hover: '#E4B45C',
        primary_dim: 'rgba(217, 164, 65, 0.12)',
        on_primary: '#15181D',
        on_background: '#E7E9EC',
        on_surface: '#B4BAC2',
        on_surface_alt: '#8A919B',
        success: '#4CC38A',
        warning: '#D9A441',
        danger: '#E5484D',
        info: '#7D8CA3',
        // Per-provider hues survive in one 4px rule per row, nowhere else.
        accent: {
          ollama: '#7FA88A',
          anthropic: '#C0885A',
          openai: '#5E9086',
          google: '#7389B8',
          mistral: '#C0726B',
          groq: '#A98C74'
        }
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '8px',
        xl: '12px',
        '2xl': '16px'
      },
      boxShadow: {
        sm: '0 1px 2px 0 rgba(0, 0, 0, 0.4)',
        md: '0 4px 10px -2px rgba(0, 0, 0, 0.5)'
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0.22, 1, 0.36, 1)'
      },
      animation: {
        'fade-in': 'fadeIn 150ms cubic-bezier(0.22, 1, 0.36, 1)'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        }
      }
    }
  },
  plugins: []
};
