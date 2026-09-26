import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEmergencyStore } from 'src/stores/emergencyStore'
import { api } from 'src/boot/axios'

vi.mock('src/boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

describe('useEmergencyStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('inicializa con estado vacío de incidentes', () => {
    const store = useEmergencyStore()
    expect(store.activeIncidents).toEqual([])
    expect(store.currentIncident).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('dispara alerta SOS y almacena el incidente en estado reactivo', async () => {
    const mockIncident = {
      id: 'inc-999',
      chief_complaint: 'Dolor torácico agudo',
      status: 'TRIGGERED',
      escalation_level: 1
    }

    api.post.mockResolvedValueOnce({ data: mockIncident })

    const store = useEmergencyStore()
    const result = await store.triggerSos({
      chief_complaint: 'Dolor torácico agudo',
      disclaimer_acknowledged: true
    })

    expect(result.id).toBe('inc-999')
    expect(store.currentIncident).toEqual(mockIncident)
  })

  it('filtra incidentes pendientes vs en curso', () => {
    const store = useEmergencyStore()
    store.activeIncidents = [
      { id: '1', status: 'TRIGGERED' },
      { id: '2', status: 'ESCALATED' },
      { id: '3', status: 'ATTENDING' }
    ]

    expect(store.pendingIncidents).toHaveLength(2)
    expect(store.inProgressIncidents).toHaveLength(1)
    expect(store.inProgressIncidents[0].id).toBe('3')
  })

  it('responde a una emergencia y actualiza su estado local', async () => {
    const store = useEmergencyStore()
    store.activeIncidents = [{ id: 'inc-1', status: 'TRIGGERED' }]

    api.post.mockResolvedValueOnce({
      data: { id: 'inc-1', status: 'ATTENDING', doctor_name: 'Dra. Méndez' }
    })

    const updated = await store.respondToIncident('inc-1')
    expect(updated.status).toBe('ATTENDING')
    expect(store.activeIncidents[0].status).toBe('ATTENDING')
  })

  it('resuelve una emergencia y la remueve de la lista activa', async () => {
    const store = useEmergencyStore()
    store.activeIncidents = [
      { id: 'inc-1', status: 'ATTENDING' },
      { id: 'inc-2', status: 'TRIGGERED' }
    ]

    api.post.mockResolvedValueOnce({
      data: { id: 'inc-1', status: 'RESOLVED', triage_notes: 'Paciente estabilizado' }
    })

    await store.resolveIncident('inc-1', 'Paciente estabilizado')
    expect(store.activeIncidents).toHaveLength(1)
    expect(store.activeIncidents[0].id).toBe('inc-2')
  })

  it('recibe evento WebSocket y actualiza o elimina incidentes en tiempo real', () => {
    const store = useEmergencyStore()
    store.activeIncidents = [{ id: 'inc-1', status: 'TRIGGERED' }]

    // Simular actualización vía WebSocket a ESCALATED
    store.updateIncidentFromWs({ id: 'inc-1', status: 'ESCALATED', escalation_level: 2 })
    expect(store.activeIncidents[0].status).toBe('ESCALATED')
    expect(store.activeIncidents[0].escalation_level).toBe(2)

    // Simular nuevo incidente entrante
    store.updateIncidentFromWs({ id: 'inc-2', status: 'TRIGGERED', chief_complaint: 'Disnea' })
    expect(store.activeIncidents).toHaveLength(2)

    // Simular resolución vía WebSocket (debe removerse de activos)
    store.updateIncidentFromWs({ id: 'inc-1', status: 'RESOLVED' })
    expect(store.activeIncidents).toHaveLength(1)
    expect(store.activeIncidents[0].id).toBe('inc-2')
  })
})
