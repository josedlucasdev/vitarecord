<template>
  <q-page class="flex items-center justify-center p-4 bg-slate-50 min-h-screen">
    <div class="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
      <!-- Header -->
      <div :class="['p-6 text-white text-center bg-gradient-to-r', portalConfig.headerGradient]">
        <div class="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-md p-2">
          <img src="/icons/vitarecord-logo.png" alt="VitaRecord" class="w-full h-full object-contain" />
        </div>
        <div class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-white/20 text-white text-2xs font-bold uppercase tracking-wider mb-2">
          <q-icon :name="portalConfig.icon" size="13px" />
          <span>{{ portalConfig.portalName }}</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight">
          {{ hasToken ? 'Restablecer Contraseña' : 'Recuperar Contraseña' }}
        </h1>
        <p class="text-slate-200 text-xs mt-1">Plataforma VitaRecord</p>
      </div>

      <div class="p-6">
        <!-- Modo 1: Solicitar Enlace (Olvidé Contraseña) -->
        <div v-if="!hasToken">
          <div v-if="!forgotSubmitted">
            <p class="text-sm text-slate-600 mb-6 leading-relaxed">
              {{ portalConfig.forgotDescription }}
            </p>

            <form class="space-y-4" @submit.prevent="submitForgotPassword">
              <q-input
                v-model="email"
                type="email"
                :label="portalConfig.emailLabel"
                filled
                required
              />

              <div v-if="forgotError" class="p-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center">
                <q-icon name="warning" class="mr-2" size="18px" />
                <span>{{ forgotError }}</span>
              </div>

              <q-btn
                type="submit"
                :color="portalConfig.btnColor"
                label="Enviar Enlace de Recuperación"
                class="w-full py-2.5 font-semibold text-white"
                no-caps
                :loading="loadingForgot"
              />
            </form>

            <div class="mt-6 text-center text-xs text-slate-500">
              ¿Te acordaste de tu contraseña?
              <router-link :to="portalConfig.loginUrl" class="font-bold hover:underline ml-1" :class="portalConfig.linkColor">
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
              <q-btn :to="portalConfig.loginUrl" outline :color="portalConfig.btnColor" label="Regresar al Login" no-caps />
            </div>
          </div>
        </div>

        <!-- Modo 2: Restablecer Contraseña con Token -->
        <div v-else>
          <div v-if="!resetSuccess">
            <p class="text-sm text-slate-600 mb-6 leading-relaxed">
              Ingresa tu nueva contraseña para actualizar el acceso a tu cuenta en {{ portalConfig.portalName }}.
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
                :color="portalConfig.btnColor"
                label="Actualizar Mi Contraseña"
                class="w-full py-2.5 font-semibold text-white"
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
              <q-btn :to="portalConfig.loginUrl" :color="portalConfig.btnColor" label="Iniciar Sesión" no-caps class="px-6 font-semibold text-white" />
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

const portalConfig = computed(() => {
  const path = route.path || ''
  const portalMeta = route.meta?.portal || ''

  if (path.includes('/clinic/') || portalMeta === 'clinic') {
    return {
      portalName: 'Personal Clínico & Médicos',
      icon: 'medical_services',
      headerGradient: 'from-cyan-800 to-teal-900',
      btnColor: 'cyan-9',
      linkColor: 'text-cyan-800',
      emailLabel: 'Correo institucional o médico',
      forgotDescription: 'Ingresa tu correo institucional o médico registrado y te enviaremos un enlace seguro para restablecer tu contraseña.',
      loginUrl: '/clinic/login'
    }
  }

  if (path.includes('/admin/') || portalMeta === 'admin') {
    return {
      portalName: 'Super Administrador',
      icon: 'admin_panel_settings',
      headerGradient: 'from-slate-800 to-indigo-950',
      btnColor: 'indigo-8',
      linkColor: 'text-indigo-800',
      emailLabel: 'Correo de superadministrador',
      forgotDescription: 'Ingresa tu correo corporativo de administración y te enviaremos un enlace de restablecimiento seguro.',
      loginUrl: '/admin/login'
    }
  }

  // Paciente por defecto
  return {
    portalName: 'Portal de Pacientes',
    icon: 'favorite',
    headerGradient: 'from-teal-700 to-emerald-900',
    btnColor: 'teal-8',
    linkColor: 'text-teal-800',
    emailLabel: 'Correo electrónico de paciente',
    forgotDescription: 'Ingresa tu correo electrónico registrado y te enviaremos un enlace seguro para restablecer tu contraseña.',
    loginUrl: '/patient/login'
  }
})

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
