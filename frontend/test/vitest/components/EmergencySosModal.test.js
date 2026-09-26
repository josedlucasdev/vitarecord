import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import EmergencySosModal from 'src/components/EmergencySosModal.vue'
import { api } from 'src/boot/axios'

vi.mock('src/boot/axios', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn()
  }
}))

vi.mock('quasar', () => ({
  useQuasar: () => ({
    notify: vi.fn()
  })
}))

describe('EmergencySosModal.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('se inicializa con campos en blanco y sin incidente activo', () => {
    const wrapper = mount(EmergencySosModal, {
      props: {
        modelValue: true
      }
    })

    expect(wrapper.vm.chiefComplaint).toBe('')
    expect(wrapper.vm.disclaimerAcknowledged).toBe(false)
    expect(wrapper.vm.activeIncident).toBeNull()
  })

  it('no permite enviar la alerta si no se ha aceptado el descargo obligatorio', async () => {
    const wrapper = mount(EmergencySosModal, {
      props: {
        modelValue: true
      }
    })

    wrapper.vm.chiefComplaint = 'Dolor agudo en pecho'
    wrapper.vm.disclaimerAcknowledged = false

    await wrapper.vm.submitSos()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('envía la alerta SOS con geolocalización y actualiza el estado activo', async () => {
    const mockCreatedIncident = {
      id: 'inc-xyz-12345678',
      chief_complaint: 'Dolor precordial intenso',
      status: 'TRIGGERED',
      escalation_level: 1,
      latitude: 10.48,
      longitude: -66.86
    }

    api.post.mockResolvedValueOnce({ data: mockCreatedIncident })

    const wrapper = mount(EmergencySosModal, {
      props: {
        modelValue: true
      }
    })

    wrapper.vm.chiefComplaint = 'Dolor precordial intenso'
    wrapper.vm.disclaimerAcknowledged = true
    wrapper.vm.latitude = 10.48
    wrapper.vm.longitude = -66.86

    await wrapper.vm.submitSos()

    expect(api.post).toHaveBeenCalledWith('/emergencies/sos', {
      chief_complaint: 'Dolor precordial intenso',
      disclaimer_acknowledged: true,
      latitude: 10.48,
      longitude: -66.86
    })

    expect(wrapper.vm.activeIncident).toEqual(mockCreatedIncident)
  })

  it('resetea el formulario al finalizar la emergencia', () => {
    const wrapper = mount(EmergencySosModal, {
      props: {
        modelValue: true
      }
    })

    wrapper.vm.chiefComplaint = 'Prueba'
    wrapper.vm.disclaimerAcknowledged = true
    wrapper.vm.activeIncident = { id: '1', status: 'RESOLVED' }

    wrapper.vm.resetForm()

    expect(wrapper.vm.chiefComplaint).toBe('')
    expect(wrapper.vm.disclaimerAcknowledged).toBe(false)
    expect(wrapper.vm.activeIncident).toBeNull()
  })
})
