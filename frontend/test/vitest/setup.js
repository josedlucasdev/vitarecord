import { config } from '@vue/test-utils'

// Configuración global de pruebas para Quasar
config.global.directives = {
  'close-popup': {}
}

const originalWarn = console.warn
console.warn = (...args) => {
  if (
    typeof args[0] === 'string' &&
    (args[0].includes('Failed to resolve component: q-') ||
      args[0].includes('Failed to resolve directive: close-popup'))
  ) {
    return
  }
  originalWarn(...args)
}
