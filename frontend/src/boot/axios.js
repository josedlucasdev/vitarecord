import { boot } from 'quasar/wrappers'
import axios from 'axios'
import { Notify } from 'quasar'
import { clearAuthToken } from 'src/composables/useAcl'

// En desarrollo, quasar.config.js reenvia /api al backend (ver
// devServer.proxy). En produccion, el reverse proxy hace el mismo trabajo
const apiBase = (process.env.API_URL || '').replace(/\/$/, '')
const api = axios.create({ baseURL: `${apiBase}/api/v1` })

let routerInstance = null

// Interceptor para inyectar token Bearer automáticamente en todas las peticiones
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para manejar expiración o pérdida de sesión (401)
api.interceptors.response.use(
  response => response,
  error => {
    const isLoginEndpoint = error.config?.url?.includes('/auth/login')

    if (error.response?.status === 401 && !isLoginEndpoint) {
      clearAuthToken()

      if (routerInstance) {
        const currentRoute = routerInstance.currentRoute.value
        if (currentRoute.name !== 'login') {
          Notify.create({
            type: 'warning',
            message: 'Tu sesión ha expirado o se ha cerrado. Por favor ingresa nuevamente.',
            position: 'top',
            timeout: 3500
          })
          routerInstance.push({
            name: 'login',
            query: currentRoute.fullPath && currentRoute.fullPath !== '/' ? { redirect: currentRoute.fullPath } : {}
          })
        }
      } else {
        const currentHash = window.location.hash || ''
        if (!currentHash.includes('/login')) {
          window.location.hash = '#/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default boot(({ app, router }) => {
  routerInstance = router
  app.config.globalProperties.$axios = axios
  app.config.globalProperties.$api = api
})

export { api }

