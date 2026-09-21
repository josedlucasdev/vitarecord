<template>
  <div class="min-h-screen w-full relative flex items-center justify-center p-4 overflow-hidden bg-gradient-to-br from-slate-100 via-indigo-50/40 to-slate-200/60">
    <!-- Cuadrícula técnica de fondo -->
    <div class="absolute inset-0 admin-grid opacity-80"></div>

    <!-- Resplandores sobrios de seguridad -->
    <div class="absolute w-[500px] h-[500px] rounded-full bg-indigo-200/40 blur-[140px] pointer-events-none -top-24 -left-24 animate-pulse-slow"></div>
    <div class="absolute w-[580px] h-[580px] rounded-full bg-blue-200/30 blur-[150px] pointer-events-none -bottom-32 -right-32 animate-pulse-slow delay-1000"></div>

    <!-- Iconos de seguridad flotantes -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="sec-float float-1">
        <svg class="w-12 h-12 text-indigo-600/18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div>
      <div class="sec-float float-2">
        <svg class="w-10 h-10 text-slate-500/20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
        </svg>
      </div>
    </div>

    <!-- Tarjeta de Login Super Administrador -->
    <q-card
      class="relative z-10 w-full max-w-md bg-white/95 backdrop-blur-xl shadow-2xl rounded-3xl border border-slate-200/80 overflow-hidden"
      style="max-width: 430px;"
    >
      <!-- Cabecera Institucional SuperAdmin -->
      <div class="bg-gradient-to-b from-indigo-50/60 to-white pt-7 pb-4 px-6 flex flex-col items-center justify-center text-center border-b border-slate-100">
        <!-- 1. Logo arriba centrado -->
        <div class="relative flex items-center justify-center mb-3">
          <div class="absolute inset-0 rounded-2xl bg-indigo-500/20 blur-md animate-pulse"></div>
          <img
            src="/icons/vitarecord-logo.png"
            alt="VitaRecord"
            class="relative w-16 h-16 rounded-2xl bg-white shadow-md p-1 border border-slate-100 object-contain mx-auto"
          />
        </div>

        <!-- 2. Luego debajo VitaRecord -->
        <h1 class="text-2xl font-black text-slate-900 tracking-tight mb-1.5">
          VitaRecord
        </h1>

        <!-- 3. Y luego Portal Super Administrador -->
        <div class="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-indigo-100/80 text-indigo-800 text-xs font-bold uppercase tracking-wider mb-1">
          <q-icon name="admin_panel_settings" size="13px" color="indigo-8" />
          <span>Portal Super Administrador</span>
        </div>

        <p class="text-xs text-slate-500 mt-1">
          Gobierno Central SaaS, Torre de Control y Aprovisionamiento
        </p>
      </div>

      <!-- Formulario de Acceso -->
      <q-card-section class="px-6 py-5 space-y-4">
        <q-form class="space-y-4" @submit.prevent="onSubmit">
          <div>
            <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              Correo de Administrador
            </label>
            <q-input
              v-model="email"
              type="email"
              placeholder="admin@vitarecord.com"
              outlined
              dense
              class="rounded-xl"
              required
              @blur="checkMfaStatus"
              @update:model-value="onEmailChange"
            >
              <template v-slot:prepend>
                <q-icon name="mail_outline" size="18px" color="indigo-7" />
              </template>
            </q-input>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide">
                Contraseña Maestra
              </label>
              <router-link
                to="/admin/forgot-password"
                class="text-xs font-semibold text-indigo-700 hover:text-indigo-900 hover:underline"
              >
                ¿Olvidaste tu contraseña?
              </router-link>
            </div>
            <q-input
              v-model="password"
              type="password"
              placeholder="••••••••••••"
              outlined
              dense
              class="rounded-xl"
              required
            >
              <template v-slot:prepend>
                <q-icon name="lock_outline" size="18px" color="indigo-7" />
              </template>
            </q-input>
          </div>

          <!-- Campo condicional de Segundo Factor MFA (Google Authenticator) -->
          <transition
            appear
            enter-active-class="animated fadeIn"
            leave-active-class="animated fadeOut"
          >
            <div v-if="showMfaField" class="space-y-1 p-3 rounded-xl bg-indigo-50/50 border border-indigo-200">
              <div class="flex items-center justify-between mb-1">
                <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide">
                  Código de Seguridad (Google Authenticator)
                </label>
                <span class="inline-flex items-center text-3xs font-bold text-indigo-800 bg-indigo-100 px-2 py-0.5 rounded-full">
                  <q-icon name="verified_user" size="11px" class="mr-1" />
                  MFA Activo
                </span>
              </div>
              <q-input
                ref="mfaInputRef"
                v-model="mfaCode"
                type="text"
                mask="######"
                placeholder="000000"
                outlined
                dense
                class="rounded-xl font-mono text-center tracking-widest text-base font-bold bg-white"
                required
              >
                <template v-slot:prepend>
                  <q-icon name="security" size="18px" color="indigo-7" />
                </template>
              </q-input>
              <p class="text-3xs text-slate-500 m-0">
                Ingresa el código temporal de 6 dígitos de tu aplicación Google Authenticator.
              </p>
            </div>
          </transition>

          <q-banner v-if="errorMessage" class="bg-red-50 text-red-800 rounded-xl text-xs border border-red-200">
            <template v-slot:avatar>
              <q-icon name="error_outline" color="red" />
            </template>
            {{ errorMessage }}
          </q-banner>

          <q-btn
            type="submit"
            color="indigo-8"
            label="Acceder como Super Administrador"
            icon-right="arrow_forward"
            :loading="loading"
            class="full-width py-2.5 rounded-xl font-bold shadow-lg shadow-indigo-800/20 text-white tracking-wide"
            no-caps
          />
        </q-form>

        <!-- Enlaces cruzados hacia los otros portales -->
        <div class="pt-3 border-t border-slate-100 text-center space-y-1.5 text-xs text-slate-500">
          <div>
            ¿Eres paciente?
            <router-link to="/patient/login" class="text-teal-700 font-bold hover:underline ml-1">
              Portal de Pacientes
            </router-link>
          </div>
          <div>
            ¿Personal clínico o médico?
            <router-link to="/clinic/login" class="text-cyan-700 font-bold hover:underline ml-1">
              Portal Personal Clínico
            </router-link>
          </div>
        </div>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from 'boot/axios'
import { setAuthToken, clearAuthToken, useAcl, getValidTokenPayload } from 'src/composables/useAcl'

const email = ref('')
const password = ref('')
const mfaCode = ref('')
const showMfaField = ref(false)
const mfaInputRef = ref(null)
const loading = ref(false)
const errorMessage = ref('')

let emailDebounceTimer = null

function onEmailChange () {
  if (emailDebounceTimer) clearTimeout(emailDebounceTimer)
  emailDebounceTimer = setTimeout(() => {
    checkMfaStatus()
  }, 500)
}

async function checkMfaStatus () {
  const cleanEmail = (email.value || '').trim().toLowerCase()
  if (!cleanEmail || !cleanEmail.includes('@')) {
    showMfaField.value = false
    return
  }
  try {
    const { data } = await api.get(`/auth/mfa-status?email=${encodeURIComponent(cleanEmail)}`)
    showMfaField.value = !!data.mfa_enabled
    if (!data.mfa_enabled) {
      mfaCode.value = ''
    }
  } catch (err) {
    // Si falla la consulta no interrumpimos el flujo
  }
}

const router = useRouter()
const { isLoggedIn } = useAcl()

const ALLOWED_ADMIN_ROLES = ['SUPERADMIN', 'COMPLIANCE_REVIEWER', 'MODERATOR']

onMounted(() => {
  if (isLoggedIn.value) {
    router.replace({ name: 'home' })
  }
})

function checkSuperAdminRoleAndRedirect (accessToken, refreshToken) {
  if (!accessToken) {
    clearAuthToken()
    errorMessage.value = 'Respuesta no válida del servidor. No se recibió credencial de acceso.'
    return false
  }
  const payload = getValidTokenPayload(accessToken)
  if (!payload || !ALLOWED_ADMIN_ROLES.includes(payload.role)) {
    clearAuthToken()
    if (payload?.role === 'PATIENT') {
      errorMessage.value = 'Acceso denegado: Este portal está restringido a Super Administradores. Si eres paciente, ingresa por el Portal de Pacientes.'
    } else {
      errorMessage.value = 'Acceso no autorizado: Se requieren privilegios de Super Administrador global para ingresar a este portal.'
    }
    return false
  }

  setAuthToken(accessToken, refreshToken)
  const redirectPath = router.currentRoute.value.query?.redirect
  if (redirectPath) {
    router.push(redirectPath)
  } else {
    router.push({ name: 'clinics-management' })
  }
  return true
}

async function onSubmit () {
  loading.value = true
  errorMessage.value = ''
  try {
    const form = new URLSearchParams()
    form.set('username', email.value)
    form.set('password', password.value)
    if (mfaCode.value) {
      form.set('mfa_code', mfaCode.value.trim().replace(/\D/g, ''))
    }

    const { data } = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    if (typeof data === 'string' && (data.includes('<!DOCTYPE') || data.includes('<html'))) {
      errorMessage.value = 'Error de conexión: El servidor devolvió una página HTML en lugar de la API. Verifica la URL del servicio.'
      return
    }

    if (!data || !data.access_token) {
      errorMessage.value = data?.detail || 'No se pudo iniciar sesión. Verifique sus credenciales.'
      return
    }

    checkSuperAdminRoleAndRedirect(data.access_token, data.refresh_token)
  } catch (err) {
    const detail = err.response?.data?.detail || ''
    if (detail.includes('MFA') || err.response?.headers?.['x-mfa-required']) {
      showMfaField.value = true
      errorMessage.value = 'Tu cuenta tiene activada la verificación en dos pasos. Por favor ingresa el código de 6 dígitos de Google Authenticator.'
      setTimeout(() => mfaInputRef.value?.focus(), 150)
      return
    }
    errorMessage.value = detail || err.message || 'Credenciales inválidas o acceso no autorizado'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-grid {
  background-size: 40px 40px;
  background-image:
    linear-gradient(to right, rgba(99, 102, 241, 0.08) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(99, 102, 241, 0.08) 1px, transparent 1px);
}

.sec-float {
  position: absolute;
}

.float-1 {
  top: 15%;
  left: 10%;
  animation: float-slow 9s ease-in-out infinite;
}

.float-2 {
  bottom: 20%;
  right: 10%;
  animation: float-slow 11s ease-in-out infinite 1s;
}

@keyframes float-slow {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(3deg);
  }
}

.animate-pulse-slow {
  animation: pulse-slow 8s ease-in-out infinite alternate;
}

@keyframes pulse-slow {
  0% {
    opacity: 0.6;
    transform: scale(0.95);
  }
  100% {
    opacity: 1;
    transform: scale(1.05);
  }
}
</style>
