import { computed, ref } from 'vue'

export const ROLE_PERMISSIONS = {
  SUPERADMIN: [
    'tenants:provision',
    'tenants:manage',
    'tenants:read',
    'system:audit_view',
    'compliance:audit_read',
    'doctors:verify',
    'compliance:verify_doctor',
    'doctors:invite',
    'rooms:read',
    'rooms:manage',
    'doctors:schedule_view',
    'doctors:schedule_manage',
    'staff:manage',
    'appointments:book',
    'appointments:manage',
    'appointments:reschedule',
    'appointments:cancel',
    'appointments:view',
    'medical_records:read',
    'clinical_records:read',
    'medical_records:write',
    'clinical_records:write',
    'payments:collect',
    'payments:record',
    'payments:view_cashier',
    'procedures:manage',
    'procedures:read',
    'consents:manage',
    'emergency:trigger',
    'emergency:monitor',
    'emergency:respond'
  ],
  COMPLIANCE_REVIEWER: [
    'tenants:read',
    'doctors:verify',
    'compliance:verify_doctor',
    'system:audit_view',
    'compliance:audit_read',
    'rooms:read',
    'medical_records:read',
    'clinical_records:read',
    'emergency:monitor',
    'emergency:respond'
  ],
  CLINIC_ADMIN: [
    'tenants:read',
    'doctors:invite',
    'rooms:read',
    'rooms:manage',
    'doctors:schedule_view',
    'doctors:schedule_manage',
    'staff:manage',
    'appointments:book',
    'appointments:manage',
    'appointments:reschedule',
    'appointments:cancel',
    'appointments:view',
    'payments:collect',
    'payments:record',
    'payments:view_cashier',
    'procedures:manage',
    'procedures:read',
    'consents:manage',
    'emergency:monitor'
  ],
  RECEPTIONIST: [
    'tenants:read',
    'rooms:read',
    'doctors:invite',
    'doctors:schedule_view',
    'appointments:book',
    'appointments:manage',
    'appointments:reschedule',
    'appointments:cancel',
    'appointments:view',
    'payments:collect',
    'payments:record',
    'payments:view_cashier',
    'procedures:read',
    'consents:manage'
  ],
  DOCTOR: [
    'tenants:read',
    'rooms:read',
    'doctors:schedule_view',
    'doctors:schedule_manage',
    'appointments:manage',
    'appointments:reschedule',
    'appointments:cancel',
    'appointments:view',
    'medical_records:read',
    'clinical_records:read',
    'medical_records:write',
    'clinical_records:write',
    'procedures:read',
    'consents:manage',
    'emergency:respond'
  ],
  PATIENT: [
    'tenants:read',
    'doctors:schedule_view',
    'appointments:book',
    'appointments:manage',
    'appointments:reschedule',
    'appointments:cancel',
    'appointments:view',
    'medical_records:read',
    'clinical_records:read',
    'procedures:read',
    'consents:manage',
    'emergency:trigger'
  ]
}

// Estado reactivo global del token
const currentToken = ref(localStorage.getItem('access_token'))

// Sincronización reactiva entre pestañas
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === 'access_token') {
      currentToken.value = event.newValue
    }
  })
}

export function isTokenExpired (token) {
  if (!token) return true
  try {
    const parts = token.split('.')
    if (parts.length < 2) return true
    const payload = JSON.parse(atob(parts[1]))
    if (!payload.exp) return false
    return payload.exp * 1000 <= Date.now()
  } catch {
    return true
  }
}

export function getValidTokenPayload (token = localStorage.getItem('access_token')) {
  if (!token) return null
  if (isTokenExpired(token)) {
    clearAuthToken()
    return null
  }
  try {
    const parts = token.split('.')
    if (parts.length < 2) {
      clearAuthToken()
      return null
    }
    return JSON.parse(atob(parts[1]))
  } catch {
    clearAuthToken()
    return null
  }
}

export function getAuthToken () {
  return localStorage.getItem('access_token')
}

export function setAuthToken (accessToken, refreshToken) {
  if (accessToken && !isTokenExpired(accessToken)) {
    localStorage.setItem('access_token', accessToken)
    if (refreshToken) localStorage.setItem('refresh_token', refreshToken)
    currentToken.value = accessToken
  } else {
    clearAuthToken()
  }
}

export function clearAuthToken () {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_role')
  currentToken.value = null
}

export function hasPermission (role, permission) {
  if (!role) return false
  const perms = ROLE_PERMISSIONS[role] || []
  return perms.includes(permission)
}

export function useAcl () {
  const tokenPayload = computed(() => {
    return getValidTokenPayload(currentToken.value)
  })

  const isLoggedIn = computed(() => !!currentToken.value && !isTokenExpired(currentToken.value))

  const user = computed(() => {
    const payload = tokenPayload.value
    if (!payload) return null
    return {
      id: payload.sub,
      email: payload.email || (payload.sub?.includes('@') ? payload.sub : ''),
      role: payload.role || 'PATIENT',
      clinicId: payload.clinic_id || null
    }
  })

  const userRole = computed(() => user.value?.role || null)

  function can (permission) {
    return hasPermission(userRole.value, permission)
  }

  function hasRole (...roles) {
    if (!userRole.value) return false
    return roles.includes(userRole.value)
  }

  return {
    currentToken,
    isLoggedIn,
    user,
    userRole,
    can,
    hasRole,
    setAuthToken,
    clearAuthToken
  }
}

