/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'JetBrains Mono', 'monospace'],
        display: ['Orbitron', 'Space Grotesk', 'sans-serif']
      },
      colors: {
        // Cyberpunk Terminal Palette
        background: '#050508',
        surface: '#0a0a10',
        surface_alt: '#11111a',
        surface_hover: '#181825',
        primary: '#00f5d4',
        primary_hover: '#33ffdb',
        primary_dim: 'rgba(0, 245, 212, 0.15)',
        secondary: '#ff006e',
        secondary_hover: '#ff3385',
        secondary_dim: 'rgba(255, 0, 110, 0.15)',
        accent: {
          ollama: '#00f5d4',
          anthropic: '#ff9f1c',
          openai: '#2ec4b6',
          google: '#4361ee',
          mistral: '#ff006e',
          groq: '#fb5607'
        },
        on_background: '#e8e8f0',
        on_surface: '#a0a0b0',
        on_surface_alt: '#707080',
        outline: '#1a1a2e',
        outline_alt: '#252540',
        outline_strong: '#353560',
        success: '#00f5d4',
        warning: '#ffbe0b',
        danger: '#ff006e',
        info: '#3a86ff',
        terminal: {
          green: '#00f5d4',
          pink: '#ff006e',
          amber: '#ffbe0b',
          blue: '#3a86ff',
          dim: '#505060'
        }
      },
      spacing: {
        '4.5': '1.125rem',
        '5.5': '1.375rem',
        '18': '4.5rem'
      },
      borderRadius: {
        'sm': '4px',
        'md': '6px',
        'lg': '8px',
        'xl': '12px',
        '2xl': '16px'
      },
      boxShadow: {
        'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.5)',
        'md': '0 4px 6px -1px rgba(0, 0, 0, 0.5)',
        'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
        'glow': '0 0 20px rgba(0, 245, 212, 0.4)',
        'glow-secondary': '0 0 20px rgba(255, 0, 110, 0.4)',
        'neon': '0 0 30px rgba(0, 245, 212, 0.3), inset 0 0 20px rgba(0, 245, 212, 0.05)',
        'terminal': 'inset 0 0 60px rgba(0, 245, 212, 0.03)',
        'border-glow': '0 0 0 1px rgba(0, 245, 212, 0.5)'
      },
      animation: {
        'fade-in': 'fadeIn 200ms ease-out',
        'slide-up': 'slideUp 300ms cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'spin-slow': 'spin 2s linear infinite',
        'cursor-blink': 'blink 1s step-end infinite',
        'scanline': 'scanline 8s linear infinite',
        'glitch': 'glitch 0.3s ease-in-out',
        'float': 'float 6s ease-in-out infinite',
        'pulse-border': 'pulseBorder 2s ease-in-out infinite'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(0, 245, 212, 0.4)' },
          '50%': { boxShadow: '0 0 40px rgba(0, 245, 212, 0.6)' }
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' }
        },
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' }
        },
        glitch: {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-2px)' },
          '40%': { transform: 'translateX(2px)' },
          '60%': { transform: 'translateX(-1px)' },
          '80%': { transform: 'translateX(1px)' }
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' }
        },
        pulseBorder: {
          '0%, 100%': { borderColor: 'rgba(0, 245, 212, 0.3)' },
          '50%': { borderColor: 'rgba(0, 245, 212, 0.6)' }
        }
      }
    }
  },
  plugins: []
};
