import { defineStore } from 'pinia'
import { api } from 'src/boot/axios'

export const useAppointmentStore = defineStore('appointment', {
  state: () => ({
    appointments: [],
    currentAppointment: null,
    loading: false,
    error: null,
    selectedDoctor: null,
    availableSlots: []
  }),

  getters: {
    upcomingAppointments: (state) => {
      const now = new Date().toISOString()
      return state.appointments.filter(a =>
        ['CONFIRMED', 'CHECKED_IN', 'IN_CONSULTATION'].includes(a.status) &&
        a.scheduled_start_time >= now
      )
    },
    pastAppointments: (state) => {
      const now = new Date().toISOString()
      return state.appointments.filter(a =>
        ['COMPLETED', 'CANCELLED', 'NO_SHOW'].includes(a.status) ||
        a.scheduled_start_time < now
      )
    }
  },

  actions: {
    async fetchMyAppointments () {
      this.loading = true
      this.error = null
      try {
        const response = await api.get('/appointments/my-appointments')
        this.appointments = response.data || []
        return this.appointments
      } catch (err) {
        this.error = err.response?.data?.detail || err.message
        throw err
      } finally {
        this.loading = false
      }
    },

    async fetchSlots (doctorId, date) {
      this.loading = true
      try {
        const response = await api.get(`/appointments/availability/${doctorId}?date=${date}`)
        this.availableSlots = response.data?.slots || []
        return this.availableSlots
      } catch (err) {
        this.availableSlots = []
        throw err
      } finally {
        this.loading = false
      }
    },

    async bookAppointment (payload) {
      this.loading = true
      this.error = null
      try {
        const response = await api.post('/appointments/book', payload)
        const newApt = response.data
        this.appointments.unshift(newApt)
        return newApt
      } catch (err) {
        this.error = err.response?.data?.detail || err.message
        throw err
      } finally {
        this.loading = false
      }
    },

    async cancelAppointment (id, reason) {
      this.loading = true
      try {
        const response = await api.post(`/appointments/${id}/cancel`, { reason })
        const updated = response.data
        const idx = this.appointments.findIndex(a => a.id === id)
        if (idx !== -1) {
          this.appointments[idx] = updated
        }
        return updated
      } catch (err) {
        this.error = err.response?.data?.detail || err.message
        throw err
      } finally {
        this.loading = false
      }
    },

    async checkInAppointment (id) {
      this.loading = true
      try {
        const response = await api.post(`/appointments/${id}/check-in`)
        const updated = response.data
        const idx = this.appointments.findIndex(a => a.id === id)
        if (idx !== -1) {
          this.appointments[idx] = updated
        }
        return updated
      } catch (err) {
        this.error = err.response?.data?.detail || err.message
        throw err
      } finally {
        this.loading = false
      }
    }
  }
})
