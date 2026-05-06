/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        tool: {
          base:    '#161b18',
          panel:   '#1a211d',
          raised:  '#222a26',
          input:   '#111614',
          border:  '#2a322e',
          brtop:   '#3d4a42',
          hover:   '#252b28',
        },
        acc: {
          green:   '#1e6b52',
          greenHi: '#45c98f',
          amber:   '#c9951c',
          amberHi: '#e4b84a',
          red:     '#f44336',
        },
        tx: {
          base:    '#c8cec9',
          dim:     '#8a938c',
          bright:  '#eeeeee',
          muted:   '#5c6560',
          accent:  '#45c98f',
          green:   '#4caf50',
        },
      },
      fontFamily: {
        ui:   ['system-ui', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['"Fira Code"', '"Cascadia Code"', 'Consolas', 'monospace'],
      },
      borderRadius: {
        sm: '2px',
        DEFAULT: '3px',
        md: '4px',
      },
    },
  },
  plugins: [],
}
