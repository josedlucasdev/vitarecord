/**
 * corePlugins.preflight = false (plan/plan.md seccion 2.A): evita que
 * Tailwind resetee los estilos nativos de los componentes Quasar.
 */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  corePlugins: {
    preflight: false
  },
  theme: {
    extend: {}
  },
  plugins: []
}
