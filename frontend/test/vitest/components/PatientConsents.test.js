import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import PatientConsents from 'src/pages/patient/PatientConsents.vue'
import { api } from 'boot/axios'

vi.mock('boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

vi.mock('quasar', () => ({
  Notify: {
    create: vi.fn()
  },
  Dialog: {
    create: vi.fn(() => ({
      onOk: (fn) => fn()
    }))
  }
}))

describe('PatientConsents.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('carga la lista de consentimientos al montar el componente', async () => {
    const mockConsents = [
      {
        id: 'c-1',
        clinic_name: 'Clínica Sanitas',
        status: 'ACTIVE',
        granted_at: '2026-09-01T00:00:00Z',
        granted_until: '2026-10-01T00:00:00Z'
      },
      {
        id: 'c-2',
        clinic_name: 'Centro Médico Metropolitano',
        status: 'REVOKED',
        granted_at: '2026-08-01T00:00:00Z',
        revoked_at: '2026-08-15T00:00:00Z'
      }
    ]

    api.get.mockResolvedValueOnce({ data: mockConsents })

    const wrapper = mount(PatientConsents)
    await wrapper.vm.$nextTick()
    // Esperar a que la promesa de load() resuelva
    await new Promise((r) => setTimeout(r, 10))

    expect(api.get).toHaveBeenCalledWith('/consents/my')
    expect(wrapper.vm.consents).toHaveLength(2)
  })

  it('otorga una nueva autorización y refresca la lista', async () => {
    api.get.mockResolvedValueOnce({ data: [] })
    const wrapper = mount(PatientConsents)
    await wrapper.vm.$nextTick()

    wrapper.vm.grantDialog.clinicId = 'clinic-abc'
    wrapper.vm.grantDialog.days = 30

    api.post.mockResolvedValueOnce({ data: { success: true } })
    api.get.mockResolvedValueOnce({
      data: [{ id: 'new-c', clinic_name: 'Nueva Clínica', status: 'ACTIVE' }]
    })

    await wrapper.vm.grant()

    expect(api.post).toHaveBeenCalledWith('/consents', {
      granted_to_clinic_id: 'clinic-abc',
      granted_days: 30
    })
    expect(wrapper.vm.grantDialog.show).toBe(false)
  })

  it('formatea etiquetas de estado correctamente', () => {
    const wrapper = mount(PatientConsents)
    expect(wrapper.vm.statusLabel('ACTIVE')).toBe('Vigente')
    expect(wrapper.vm.statusLabel('REVOKED')).toBe('Revocado')
    expect(wrapper.vm.statusLabel('EXPIRED')).toBe('Vencido')
  })
})
