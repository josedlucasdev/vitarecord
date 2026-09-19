import { configure } from 'quasar/wrappers'

export default configure(function (/* ctx */) {
  return {
    boot: ['axios'],

    css: ['app.css'],

    extras: ['roboto-font', 'material-icons'],

    build: {
      target: {
        browser: ['es2019', 'edge88', 'firefox78', 'chrome87', 'safari13.1'],
        node: 'node20'
      },
      vueRouterMode: 'hash',
      env: {
        API_URL: process.env.CLIENT_API_URL || ''
      }
    },

    devServer: {
      host: '0.0.0.0',
      port: 9000,
      open: false,
      proxy: {
        '/api': {
          target: process.env.API_URL || 'http://backend:8000',
          changeOrigin: true
        }
      }
    },

    framework: {
      config: {
        brand: {
          primary: '#24796a'
        }
      },
      plugins: ['Notify', 'Dialog', 'Loading']
    },

    animations: [],

    pwa: {
      workboxMode: 'GenerateSW'
    },

    capacitor: {
      hideSplashscreen: true
    }
  }
})
