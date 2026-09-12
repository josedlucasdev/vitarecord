import { route } from 'quasar/wrappers'
import { createMemoryHistory, createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import { Notify } from 'quasar'
import routes from './routes'
import { clearAuthToken, getValidTokenPayload, hasPermission } from 'src/composables/useAcl'

export default route(function () {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : (process.env.VUE_ROUTER_MODE === 'history' ? createWebHistory : createWebHashHistory)

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,
    history: createHistory(process.env.VUE_ROUTER_BASE)
  })

  // Navigation Guard: Autenticación estricta, caducidad de sesión y control de permisos ACL
  Router.beforeEach((to, from, next) => {
    const validPayload = getValidTokenPayload()
    const isAuthenticated = !!validPayload

    // 1. Rutas que requieren autenticación: si no hay sesión o expiró, siempre al login
    if (to.matched.some(record => record.meta.requiresAuth)) {
      if (!isAuthenticated) {
        clearAuthToken()
        return next({
          name: 'login',
          query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : {}
        })
      }

      // Verificación de permiso atómico ACL si la ruta lo exige
      const requiredPerm = to.meta.requiredPermission
      if (requiredPerm) {
        const role = validPayload.role
        if (!hasPermission(role, requiredPerm)) {
          Notify.create({
            type: 'warning',
            message: 'Acceso restringido: tu rol no tiene los permisos necesarios para esta sección.'
          })
          return next({ name: 'home' })
        }
      }
    }

    // 2. Rutas para invitados (Login, Recuperación): si ya tiene sesión activa, redirigir adentro
    if (to.matched.some(record => record.meta.guestOnly)) {
      if (isAuthenticated) {
        return next({ name: 'home' })
      }
    }

    next()
  })

  return Router
})
