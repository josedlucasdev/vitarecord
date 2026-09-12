<template>
  <q-page class="flex items-center justify-center p-4 bg-slate-50 min-h-screen">
    <div class="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
      <!-- Header -->
      <div class="bg-gradient-to-r from-slate-800 to-slate-900 p-6 text-white text-center">
        <div class="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-md p-2">
          <img src="/icons/vitarecord-logo.png" alt="VitaRecord" class="w-full h-full object-contain" />
        </div>
        <h1 class="text-2xl font-bold tracking-tight">
          {{ hasToken ? 'Restablecer Contraseña' : 'Recuperar Contraseña' }}
        </h1>
        <p class="text-slate-300 text-sm mt-1">Plataforma VitaRecord</p>
      </div>

      <div class="p-6">
        <!-- Modo 1: Solicitar Enlace (Olvidé Contraseña) -->
        <div v-if="!hasToken">
          <div v-if="!forgotSubmitted">
            <p class="text-sm text-slate-600 mb-6 leading-relaxed">
              Ingresa tu correo electrónico registrado y te enviaremos un enlace seguro para restablecer tu contraseña.
            </p>

            <form class="space-y-4" @submit.prevent="submitForgotPassword">
              <q-input
                v-model="email"
                type="email"
                label="Correo electrónico"
                filled
                required
              />

              <div v-if="forgotError" class="p-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center">
                <q-icon name="warning" class="mr-2" size="18px" />
                <span>{{ forgotError }}</span>
              </div>

              <q-btn
                type="submit"
                color="primary"
                label="Enviar Enlace de Recuperación"
                class="w-full py-2.5 font-semibold"
                no-caps
                :loading="loadingForgot"
              />
            </form>

            <div class="mt-6 text-center text-xs text-slate-500">
              ¿Te acordaste de tu contraseña?
              <router-link to="/login" class="text-primary font-semibold hover:underline ml-1">
                Iniciar Sesión
              </router-link>
            </div>
          </div>

          <div v-else class="text-center py-4">
            <div class="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-3">
              <q-icon name="mark_email_read" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-800">Revisa tu Correo</h3>
            <p class="text-slate-600 text-sm mt-2">
              Hemos procesado tu solicitud. Si el correo <strong>{{ email }}</strong> está registrado, recibirás un enlace válido por 1 hora.
            </p>
            <div class="mt-6">
              <q-btn to="/login" outline color="primary" label="Regresar al Login" no-caps />
            </div>
          </div>
        </div>

        <!-- Modo 2: Restablecer Contraseña con Token -->
        <div v-else>
          <div v-if="!resetSuccess">
            <p class="text-sm text-slate-600 mb-6 leading-relaxed">
              Ingresa tu nueva contraseña para actualizar el acceso a tu cuenta.
            </p>

            <form class="space-y-4" @submit.prevent="submitResetPassword">
              <q-input
                v-model="newPassword"
                type="password"
                label="Nueva Contraseña"
                filled
                hint="Mínimo 8 caracteres"
                required
              />
              <q-input
                v-model="confirmPassword"
                type="password"
                label="Confirmar Contraseña"
                filled
                :error="passwordMismatch"
                error-message="Las contraseñas no coinciden"
                required
              />

              <div v-if="resetError" class="p-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center">
                <q-icon name="warning" class="mr-2" size="18px" />
                <span>{{ resetError }}</span>
              </div>

              <q-btn
                type="submit"
                color="primary"
                label="Actualizar Mi Contraseña"
                class="w-full py-2.5 font-semibold"
                no-caps
                :loading="loadingReset"
                :disable="!canSubmitReset"
              />
            </form>
          </div>

          <div v-else class="text-center py-4">
            <div class="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-3">
              <q-icon name="check_circle" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-800">¡Contraseña Actualizada!</h3>
            <p class="text-slate-600 text-sm mt-2">
              Tu contraseña ha sido restablecida exitosamente. Todas las sesiones anteriores han sido revocadas por seguridad.
            </p>
            <div class="mt-6">
              <q-btn to="/login" color="primary" label="Iniciar Sesión" no-caps class="px-6 font-semibold" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'boot/axios'

const route = useRoute()

const hasToken = ref(false)
const token = ref('')

// Modo Forgot
const email = ref('')
const loadingForgot = ref(false)
const forgotSubmitted = ref(false)
const forgotError = ref('')

// Modo Reset
const newPassword = ref('')
const confirmPassword = ref('')
const loadingReset = ref(false)
const resetError = ref('')
const resetSuccess = ref(false)

const passwordMismatch = computed(() => {
  return confirmPassword.value.length > 0 && newPassword.value !== confirmPassword.value
})

const canSubmitReset = computed(() => {
  return newPassword.value.length >= 8 && newPassword.value === confirmPassword.value
})

onMounted(() => {
  token.value = route.query.token || ''
  hasToken.value = Boolean(token.value)
})

async function submitForgotPassword() {
  loadingForgot.value = true
  forgotError.value = ''
  try {
    await api.post('/auth/forgot-password', { email: email.value })
    forgotSubmitted.value = true
  } catch (err) {
    forgotError.value = err.response?.data?.detail || 'No se pudo enviar la solicitud.'
  } finally {
    loadingForgot.value = false
  }
}

async function submitResetPassword() {
  loadingReset.value = true
  resetError.value = ''
  try {
    await api.post('/auth/reset-password', {
      token: token.value,
      new_password: newPassword.value
    })
    resetSuccess.value = true
  } catch (err) {
    resetError.value = err.response?.data?.detail || 'Token inválido o expirado. Solicita un nuevo enlace.'
  } finally {
    loadingReset.value = false
  }
}
</script>
