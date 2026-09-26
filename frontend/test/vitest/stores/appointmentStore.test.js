import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAppointmentStore } from 'src/stores/appointmentStore'
import { api } from 'src/boot/axios'

vi.mock('src/boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

describe('useAppointmentStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('inicializa con lista de citas vacía', () => {
    const store = useAppointmentStore()
    expect(store.appointments).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('obtiene las citas del usuario y las separa en próximas y pasadas', async () => {
    const futureDate = new Date(Date.now() + 86400000).toISOString()
    const pastDate = new Date(Date.now() - 86400000).toISOString()

    const mockAppointments = [
      {
        id: 'apt-1',
        doctor_id: 'doc-1',
        scheduled_start_time: futureDate,
        status: 'CONFIRMED'
      },
      {
        id: 'apt-2',
        doctor_id: 'doc-2',
        scheduled_start_time: pastDate,
        status: 'COMPLETED'
      }
    ]

    api.get.mockResolvedValueOnce({ data: mockAppointments })

    const store = useAppointmentStore()
    await store.fetchMyAppointments()

    expect(store.appointments).toHaveLength(2)
    expect(store.upcomingAppointments).toHaveLength(1)
    expect(store.upcomingAppointments[0].id).toBe('apt-1')
    expect(store.pastAppointments).toHaveLength(1)
    expect(store.pastAppointments[0].id).toBe('apt-2')
  })

  it('agenda una nueva cita y la añade a la colección', async () => {
    const newApt = {
      id: 'apt-new',
      doctor_id: 'doc-1',
      scheduled_start_time: '2026-10-01T10:00:00Z',
      status: 'CONFIRMED'
    }

    api.post.mockResolvedValueOnce({ data: newApt })

    const store = useAppointmentStore()
    const result = await store.bookAppointment({
      doctor_id: 'doc-1',
      start_time: '2026-10-01T10:00:00Z'
    })

    expect(result.id).toBe('apt-new')
    expect(store.appointments).toHaveLength(1)
    expect(store.appointments[0].id).toBe('apt-new')
  })

  it('cancela una cita actualizando su estado reactivamente', async () => {
    const store = useAppointmentStore()
    store.appointments = [
      { id: 'apt-1', status: 'CONFIRMED' },
      { id: 'apt-2', status: 'CONFIRMED' }
    ]

    api.post.mockResolvedValueOnce({
      data: { id: 'apt-1', status: 'CANCELLED', cancellation_reason: 'Imprevisto' }
    })

    const updated = await store.cancelAppointment('apt-1', 'Imprevisto')
    expect(updated.status).toBe('CANCELLED')
    expect(store.appointments[0].status).toBe('CANCELLED')
    expect(store.appointments[1].status).toBe('CONFIRMED')
  })

  it('realiza check-in actualizando a CHECKED_IN', async () => {
    const store = useAppointmentStore()
    store.appointments = [{ id: 'apt-1', status: 'CONFIRMED' }]

    api.post.mockResolvedValueOnce({
      data: { id: 'apt-1', status: 'CHECKED_IN' }
    })

    const updated = await store.checkInAppointment('apt-1')
    expect(updated.status).toBe('CHECKED_IN')
    expect(store.appointments[0].status).toBe('CHECKED_IN')
  })
})
