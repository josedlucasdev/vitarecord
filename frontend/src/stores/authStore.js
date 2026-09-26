import { defineStore } from 'pinia'
import { api } from 'src/boot/axios'
import {
  currentToken,
  getValidTokenPayload,
  isTokenExpired,
  setAuthToken,
  clearAuthToken,
  hasPermission
} from 'src/composables/useAcl'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: (typeof localStorage !== 'undefined' && localStorage.getItem('access_token')) || null,
    refreshToken: (typeof localStorage !== 'undefined' && localStorage.getItem('refresh_token')) || null,
    user: null,
    loading: false,
    mfaRequired: false,
    mfaTempToken: null
  }),

  getters: {
    isAuthenticated: (state) => !!state.token && !isTokenExpired(state.token),
    role: (state) => state.user?.role || null,
    clinicId: (state) => state.user?.clinicId || null,
    can: (state) => (permission) => hasPermission(state.user?.role, permission)
  },

  actions: {
    initAuth () {
      const payload = getValidTokenPayload(this.token)
      if (payload) {
        this.user = {
          id: payload.sub,
          email: payload.email || (payload.sub?.includes('@') ? payload.sub : ''),
          role: payload.role || 'PATIENT',
          clinicId: payload.clinic_id || null
        }
      } else {
        this.clearAuth()
      }
    },

    setTokens (accessToken, refreshToken) {
      this.token = accessToken
      this.refreshToken = refreshToken || null
      setAuthToken(accessToken, refreshToken)
      this.initAuth()
    },

    clearAuth () {
      this.token = null
      this.refreshToken = null
      this.user = null
      this.mfaRequired = false
      this.mfaTempToken = null
      clearAuthToken()
    },

    async login (credentials) {
      this.loading = true
      try {
        const response = await api.post('/auth/login', credentials)
        const data = response.data
        if (data.mfa_required) {
          this.mfaRequired = true
          this.mfaTempToken = data.temp_token
          return { mfaRequired: true }
        }
        this.setTokens(data.access_token, data.refresh_token)
        return { success: true, user: this.user }
      } finally {
        this.loading = false
      }
    },

    async logout () {
      try {
        if (this.token) {
          await api.post('/auth/logout').catch(() => {})
        }
      } finally {
        this.clearAuth()
      }
    }
  }
})
