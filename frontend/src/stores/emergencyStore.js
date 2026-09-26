import { defineStore } from 'pinia'
import { api } from 'src/boot/axios'

export const useEmergencyStore = defineStore('emergency', {
  state: () => ({
    activeIncidents: [],
    currentIncident: null,
    loading: false,
    error: null,
    connectionStatus: 'DISCONNECTED'
  }),

  getters: {
    pendingIncidents: (state) => {
      return state.activeIncidents.filter(i => ['TRIGGERED', 'ESCALATED'].includes(i.status))
    },
    inProgressIncidents: (state) => {
      return state.activeIncidents.filter(i => i.status === 'ATTENDING')
    }
  },

  actions: {
    async triggerSos (payload) {
      this.loading = true
      this.error = null
      try {
        const response = await api.post('/emergencies/trigger', payload)
        this.currentIncident = response.data
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || err.message
        throw err
      } finally {
        this.loading = false
      }
    },

    async fetchActiveIncidents () {
      this.loading = true
      try {
        const response = await api.get('/emergencies/active')
        this.activeIncidents = response.data || []
        return this.activeIncidents
      } catch (err) {
        this.error = err.response?.data?.detail || err.message
        throw err
      } finally {
        this.loading = false
      }
    },

    async respondToIncident (incidentId) {
      this.loading = true
      try {
        const response = await api.post(`/emergencies/${incidentId}/respond`)
        const updated = response.data
        const idx = this.activeIncidents.findIndex(i => i.id === incidentId)
        if (idx !== -1) {
          this.activeIncidents[idx] = updated
        }
        return updated
      } catch (err) {
        this.error = err.response?.data?.detail || err.message
        throw err
      } finally {
        this.loading = false
      }
    },

    async resolveIncident (incidentId, triageNotes) {
      this.loading = true
      try {
        const response = await api.post(`/emergencies/${incidentId}/resolve`, {
          triage_notes: triageNotes
        })
        const updated = response.data
        this.activeIncidents = this.activeIncidents.filter(i => i.id !== incidentId)
        if (this.currentIncident?.id === incidentId) {
          this.currentIncident = updated
        }
        return updated
      } catch (err) {
        this.error = err.response?.data?.detail || err.message
        throw err
      } finally {
        this.loading = false
      }
    },

    updateIncidentFromWs (incidentData) {
      const idx = this.activeIncidents.findIndex(i => i.id === incidentData.id)
      if (idx !== -1) {
        if (incidentData.status === 'RESOLVED') {
          this.activeIncidents.splice(idx, 1)
        } else {
          this.activeIncidents[idx] = incidentData
        }
      } else if (incidentData.status !== 'RESOLVED') {
        this.activeIncidents.unshift(incidentData)
      }

      if (this.currentIncident?.id === incidentData.id) {
        this.currentIncident = incidentData
      }
    }
  }
})
