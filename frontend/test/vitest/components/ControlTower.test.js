import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ControlTower from 'src/pages/admin/ControlTower.vue'
import { api } from 'src/boot/axios'

vi.mock('src/boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

vi.mock('quasar', () => ({
  useQuasar: () => ({
    notify: vi.fn()
  }),
  Dialog: {
    create: vi.fn()
  },
  date: {
    formatDate: vi.fn((val) => val)
  }
}))

// Mock de WebSocket global
global.WebSocket = vi.fn().mockImplementation(() => ({
  send: vi.fn(),
  close: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn()
}))

// Mock de Audio
global.Audio = vi.fn().mockImplementation(() => ({
  play: vi.fn().mockResolvedValue(),
  pause: vi.fn()
}))

describe('ControlTower.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: [] })
  })

  it('calcula métricas de incidentes por nivel de escalamiento', () => {
    const wrapper = mount(ControlTower)
    wrapper.vm.incidents = [
      { id: '1', escalation_level: 1, status: 'TRIGGERED' },
      { id: '2', escalation_level: 2, status: 'ESCALATED' },
      { id: '3', escalation_level: 2, status: 'ESCALATED' },
      { id: '4', escalation_level: 4, status: 'RESOLVED' }
    ]

    expect(wrapper.vm.countByLevel(1)).toBe(1)
    expect(wrapper.vm.countByLevel(2)).toBe(2)
    expect(wrapper.vm.countByLevel(3)).toBe(0)
    expect(wrapper.vm.countByLevel(4)).toBe(1)
  })

  it('carga incidentes activos al iniciar', async () => {
    const mockData = [
      {
        id: 'inc-100',
        chief_complaint: 'Taquicardia severa',
        status: 'TRIGGERED',
        escalation_level: 1,
        created_at: new Date().toISOString()
      }
    ]
    api.get.mockResolvedValue({ data: mockData })

    const wrapper = mount(ControlTower)
    await wrapper.vm.loadActiveIncidents()

    expect(api.get).toHaveBeenCalledWith('/emergencies/active')
    expect(wrapper.vm.incidents).toHaveLength(1)
    expect(wrapper.vm.incidents[0].chief_complaint).toBe('Taquicardia severa')
  })

  it('permite escalar un incidente manualmente', async () => {
    api.post.mockResolvedValueOnce({
      data: { id: 'inc-100', escalation_level: 2, status: 'ESCALATED' }
    })
    api.get.mockResolvedValueOnce({ data: [] })

    const wrapper = mount(ControlTower)
    await wrapper.vm.escalateIncident('inc-100')

    expect(api.post).toHaveBeenCalledWith('/emergencies/inc-100/escalate')
  })
})
