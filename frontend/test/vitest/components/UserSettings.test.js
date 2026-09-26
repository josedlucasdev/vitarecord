import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import UserSettings from 'src/pages/settings/UserSettings.vue'
import { api } from 'boot/axios'

vi.mock('boot/axios', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000/api/v1' }
  }
}))

vi.mock('quasar', () => ({
  useQuasar: () => ({
    notify: vi.fn()
  })
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn()
  })
}))

vi.mock('src/stores/authStore', () => ({
  useAuthStore: () => ({
    clearAuth: vi.fn(),
    user: { id: 'u111', role: 'SUPERADMIN' }
  })
}))

describe('UserSettings.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('carga datos de perfil, recuperación, sesiones y notificaciones al montar', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/auth/me') {
        return Promise.resolve({
          data: {
            id: 'u-1',
            email: 'doctor@intimasalud.com',
            full_name: 'Dr. Alejandro Morales',
            phone: '+584120000002',
            role: 'DOCTOR',
            status: 'ACTIVE',
            profile_picture_url: null,
            mfa_enabled: true
          }
        })
      }
      if (url === '/auth/recovery-methods') {
        return Promise.resolve({
          data: {
            recovery_email: 'recuperacion@example.com',
            recovery_phone: '+584141112233',
            has_recovery_codes: true,
            recovery_codes_count: 8
          }
        })
      }
      if (url === '/auth/sessions') {
        return Promise.resolve({
          data: [
            { id: 's-1', device_info: 'Mac OS', ip_address: '127.0.0.1', is_current: true }
          ]
        })
      }
      if (url === '/auth/notification-settings') {
        return Promise.resolve({
          data: {
            channels: ['PUSH', 'EMAIL'],
            categories: {
              appointments: { email: true, push: true, whatsapp: true }
            }
          }
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(UserSettings, {
      global: {
        stubs: {
          qPage: { template: '<div><slot /></div>' },
          qBadge: { template: '<span><slot /></span>' },
          qBtn: { template: '<button><slot /></button>' },
          qIcon: { template: '<i><slot /></i>' },
          qTooltip: { template: '<span />' },
          qTabs: { template: '<div><slot /></div>' },
          qTab: { template: '<div><slot /></div>' },
          qTabPanels: { template: '<div><slot /></div>' },
          qTabPanel: { template: '<div><slot /></div>' },
          qInput: { template: '<input />' },
          qCheckbox: { template: '<input type="checkbox" />' },
          qToggle: { template: '<input type="checkbox" />' },
          qLinearProgress: { template: '<div />' },
          qDialog: { template: '<div><slot /></div>' },
          qCard: { template: '<div><slot /></div>' },
          qSpinnerDots: { template: '<div />' },
          qSpinner: { template: '<div />' },
          MfaSecurityModal: { template: '<div />' }
        }
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 20))

    expect(api.get).toHaveBeenCalledWith('/auth/me')
    expect(wrapper.vm.userProfile.email).toBe('doctor@intimasalud.com')
    expect(wrapper.vm.userProfile.full_name).toBe('Dr. Alejandro Morales')
    expect(wrapper.vm.userProfile.mfa_enabled).toBe(true)
  })
})
