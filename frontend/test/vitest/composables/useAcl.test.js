import { describe, it, expect, beforeEach } from 'vitest'
import {
  ROLE_PERMISSIONS,
  hasPermission,
  isTokenExpired,
  getValidTokenPayload,
  useAcl
} from 'src/composables/useAcl'

function createMockJwt (payload) {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  return `${header}.${body}.mockSignature`
}

describe('useAcl & ROLE_PERMISSIONS', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('valida permisos para SUPERADMIN', () => {
    expect(hasPermission('SUPERADMIN', 'tenants:provision')).toBe(true)
    expect(hasPermission('SUPERADMIN', 'procedures:manage')).toBe(true)
    expect(hasPermission('SUPERADMIN', 'procedures:read')).toBe(true)
    expect(hasPermission('SUPERADMIN', 'consents:manage')).toBe(true)
    expect(hasPermission('SUPERADMIN', 'compliance:audit_read')).toBe(true)
  })

  it('valida permisos para CLINIC_ADMIN', () => {
    expect(hasPermission('CLINIC_ADMIN', 'procedures:manage')).toBe(true)
    expect(hasPermission('CLINIC_ADMIN', 'procedures:read')).toBe(true)
    expect(hasPermission('CLINIC_ADMIN', 'consents:manage')).toBe(true)
    expect(hasPermission('CLINIC_ADMIN', 'tenants:provision')).toBe(false)
  })

  it('valida permisos para DOCTOR y PATIENT', () => {
    expect(hasPermission('DOCTOR', 'procedures:read')).toBe(true)
    expect(hasPermission('DOCTOR', 'medical_records:write')).toBe(true)
    expect(hasPermission('DOCTOR', 'procedures:manage')).toBe(false)

    expect(hasPermission('PATIENT', 'appointments:book')).toBe(true)
    expect(hasPermission('PATIENT', 'emergency:trigger')).toBe(true)
    expect(hasPermission('PATIENT', 'consents:manage')).toBe(true)
    expect(hasPermission('PATIENT', 'medical_records:write')).toBe(false)
  })

  it('detecta correctamente tokens expirados y vigentes', () => {
    const expiredExp = Math.floor(Date.now() / 1000) - 3600
    const validExp = Math.floor(Date.now() / 1000) + 3600

    const expiredToken = createMockJwt({ sub: 'user1', exp: expiredExp })
    const validToken = createMockJwt({ sub: 'user2', exp: validExp })

    expect(isTokenExpired(expiredToken)).toBe(true)
    expect(isTokenExpired(validToken)).toBe(false)
    expect(isTokenExpired(null)).toBe(true)
    expect(isTokenExpired('malformed.token')).toBe(true)
  })

  it('extrae el payload del token válido', () => {
    const validExp = Math.floor(Date.now() / 1000) + 3600
    const token = createMockJwt({
      sub: 'dr.garcia@vitarecord.com',
      role: 'DOCTOR',
      clinic_id: 'cl-77',
      exp: validExp
    })

    const payload = getValidTokenPayload(token)
    expect(payload).not.toBeNull()
    expect(payload.sub).toBe('dr.garcia@vitarecord.com')
    expect(payload.role).toBe('DOCTOR')
    expect(payload.clinic_id).toBe('cl-77')
  })

  it('hook useAcl refleja reactivamente el usuario y sus capacidades', () => {
    const validExp = Math.floor(Date.now() / 1000) + 3600
    const token = createMockJwt({
      sub: 'recepcion@vitarecord.com',
      role: 'RECEPTIONIST',
      clinic_id: 'cl-1',
      exp: validExp
    })

    const acl = useAcl()
    acl.setAuthToken(token)

    expect(acl.isLoggedIn.value).toBe(true)
    expect(acl.userRole.value).toBe('RECEPTIONIST')
    expect(acl.hasRole('RECEPTIONIST')).toBe(true)
    expect(acl.hasRole('SUPERADMIN')).toBe(false)
    expect(acl.can('appointments:book')).toBe(true)
    expect(acl.can('tenants:manage')).toBe(false)

    acl.clearAuthToken()
    expect(acl.isLoggedIn.value).toBe(false)
    expect(acl.user.value).toBeNull()
  })
})
