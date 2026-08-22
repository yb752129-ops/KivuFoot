/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        pitch: '#0B1F17',      // vert nuit, fond principal
        pitchLine: '#173226',  // lignes de terrain
        gold: '#D4AF37',       // accent victoire / vérifié
        clay: '#C1502E',       // accent alerte / en vérification
        chalk: '#F4F1EA',      // texte clair
      },
      fontFamily: {
        display: ['"Bebas Neue"', 'Impact', 'sans-serif'],
        body: ['"Inter"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
