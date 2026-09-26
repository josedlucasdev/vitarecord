import { boot } from 'quasar/wrappers'
import axios from 'axios'
import { Notify } from 'quasar'
import { clearAuthToken } from 'src/composables/useAcl'

// En desarrollo, quasar.config.js reenvia /api al backend (ver
// devServer.proxy). En produccion, se apunta al dominio del API.
let apiBase = (process.env.CLIENT_API_URL || process.env.API_URL || process.env.VITE_API_URL || '').replace(/\/$/, '')
if (typeof window !== 'undefined') {
  if (apiBase.includes('backend') || apiBase.includes('localhost:9000')) {
    apiBase = ''
  }
  // En producción (app.vitarecord.com), si apiBase está vacío o no es una URL absoluta válida, usar api.vitarecord.com
  if (!apiBase && (window.location.hostname === 'app.vitarecord.com' || window.location.hostname.endsWith('vitarecord.com'))) {
    apiBase = 'https://api.vitarecord.com'
  }
}
const api = axios.create({ baseURL: `${apiBase}/api/v1` })

export function getApiBaseUrl () {
  return apiBase
}

export function resolveApiUrl (url) {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:') || url.startsWith('blob:')) {
    return url
  }
  const base = getApiBaseUrl()
  const cleanPath = url.startsWith('/') ? url : `/${url}`
  return base ? `${base}${cleanPath}` : cleanPath
}

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

    // MFA obligatorio por rol (plan 2.B.9): avisar al layout para abrir el asistente.
    const detail = error.response?.data?.detail
    if (error.response?.status === 403 && typeof detail === 'string' && detail.startsWith('MFA_SETUP_REQUIRED')) {
      window.dispatchEvent(new CustomEvent('vitarecord:mfa-setup-required'))
    }

    if (error.response?.status === 401 && !isLoginEndpoint) {
      clearAuthToken()

      if (routerInstance) {
        const currentRoute = routerInstance.currentRoute.value
        const isAuthPage = ['patient-login', 'clinic-login', 'admin-login', 'login'].includes(currentRoute.name)
        if (!isAuthPage) {
          Notify.create({
            type: 'warning',
            message: 'Tu sesión ha expirado o se ha cerrado. Por favor ingresa nuevamente.',
            position: 'top',
            timeout: 3500
          })

          let targetLogin = 'patient-login'
          if (currentRoute.path.startsWith('/admin')) {
            targetLogin = 'admin-login'
          } else if (currentRoute.path.startsWith('/clinic') || currentRoute.path.startsWith('/doctor')) {
            targetLogin = 'clinic-login'
          }

          routerInstance.push({
            name: targetLogin,
            query: currentRoute.fullPath && currentRoute.fullPath !== '/' && currentRoute.fullPath !== '/dashboard' ? { redirect: currentRoute.fullPath } : {}
          })
        }
      } else {
        const currentHash = window.location.hash || ''
        if (!currentHash.includes('login')) {
          window.location.hash = '#/patient/login'
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

