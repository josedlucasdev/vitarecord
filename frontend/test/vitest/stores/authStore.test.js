import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from 'src/stores/authStore'
import { api } from 'src/boot/axios'

vi.mock('src/boot/axios', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn()
  }
}))

// Helper para crear un JWT mock no expirado
function createMockJwt (payload) {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  return `${header}.${body}.mockSignature`
}

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('inicializa con estado vacío si no hay token', () => {
    const store = useAuthStore()
    expect(store.token).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })

  it('inicializa sesión correctamente desde token válido existente', () => {
    const validExp = Math.floor(Date.now() / 1000) + 3600
    const token = createMockJwt({
      sub: 'doctor@vitarecord.com',
      role: 'DOCTOR',
      clinic_id: 'clinic-123',
      exp: validExp
    })

    const store = useAuthStore()
    store.setTokens(token, 'refresh-xyz')

    expect(store.isAuthenticated).toBe(true)
    expect(store.token).toBe(token)
    expect(store.user).toEqual({
      id: 'doctor@vitarecord.com',
      email: 'doctor@vitarecord.com',
      role: 'DOCTOR',
      clinicId: 'clinic-123'
    })
    expect(store.role).toBe('DOCTOR')
    expect(store.clinicId).toBe('clinic-123')
  })

  it('evalúa permisos de acuerdo al rol del usuario autenticado', () => {
    const validExp = Math.floor(Date.now() / 1000) + 3600
    const token = createMockJwt({
      sub: 'superadmin@vitarecord.com',
      role: 'SUPERADMIN',
      exp: validExp
    })

    const store = useAuthStore()
    store.setTokens(token)

    expect(store.can('tenants:manage')).toBe(true)
    expect(store.can('procedures:manage')).toBe(true)
    expect(store.can('consents:manage')).toBe(true)
  })

  it('maneja login exitoso y guarda tokens en el store y localStorage', async () => {
    const validExp = Math.floor(Date.now() / 1000) + 3600
    const token = createMockJwt({
      sub: 'patient@vitarecord.com',
      role: 'PATIENT',
      exp: validExp
    })

    api.post.mockResolvedValueOnce({
      data: {
        access_token: token,
        refresh_token: 'refresh-abc'
      }
    })

    const store = useAuthStore()
    const result = await store.login({ email: 'patient@vitarecord.com', password: 'secretpassword' })

    expect(result.success).toBe(true)
    expect(store.isAuthenticated).toBe(true)
    expect(store.role).toBe('PATIENT')
    expect(localStorage.getItem('access_token')).toBe(token)
  })

  it('detecta requerimiento de MFA durante el login', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        mfa_required: true,
        temp_token: 'mfa-temp-token-999'
      }
    })

    const store = useAuthStore()
    const result = await store.login({ email: 'admin@vitarecord.com', password: 'secretpassword' })

    expect(result.mfaRequired).toBe(true)
    expect(store.mfaRequired).toBe(true)
    expect(store.mfaTempToken).toBe('mfa-temp-token-999')
    expect(store.isAuthenticated).toBe(false)
  })

  it('limpia credenciales y tokens al cerrar sesión (logout)', async () => {
    const validExp = Math.floor(Date.now() / 1000) + 3600
    const token = createMockJwt({ sub: 'user@vitarecord.com', role: 'PATIENT', exp: validExp })

    const store = useAuthStore()
    store.setTokens(token, 'refresh-xyz')
    expect(store.isAuthenticated).toBe(true)

    api.post.mockResolvedValueOnce({ data: { message: 'Logged out' } })
    await store.logout()

    expect(store.isAuthenticated).toBe(false)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})
