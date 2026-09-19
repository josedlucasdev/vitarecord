<template>
  <div class="min-h-screen w-full relative flex items-center justify-center p-4 overflow-hidden bg-gradient-to-br from-slate-100 via-cyan-50/40 to-teal-100/60">
    <!-- Cuadrícula médica de fondo -->
    <div class="absolute inset-0 medical-grid opacity-80"></div>

    <!-- Resplandores suaves -->
    <div class="absolute w-[520px] h-[520px] rounded-full bg-cyan-200/40 blur-[140px] pointer-events-none -top-24 -right-24 animate-pulse-slow"></div>
    <div class="absolute w-[580px] h-[580px] rounded-full bg-teal-200/40 blur-[150px] pointer-events-none -bottom-32 -left-32 animate-pulse-slow delay-1000"></div>

    <!-- Elementos médicos flotantes -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="med-float float-1">
        <svg class="w-10 h-10 text-cyan-700/18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div>
      <div class="med-float float-2">
        <svg class="w-8 h-8 text-teal-600/20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 10.5h-5.5V5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v5.5H5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5h5.5V19c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-5.5H19c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z"/>
        </svg>
      </div>
    </div>

    <!-- Tarjeta de Login del Personal Clínico -->
    <q-card
      class="relative z-10 w-full max-w-md bg-white/95 backdrop-blur-xl shadow-2xl rounded-3xl border border-slate-200/80 overflow-hidden"
      style="max-width: 430px;"
    >
      <!-- Cabecera Institucional VitaRecord Clínico -->
      <div class="bg-gradient-to-b from-cyan-50/60 to-white pt-7 pb-4 px-6 text-center border-b border-slate-100">
        <div class="relative inline-flex items-center justify-center mb-2.5">
          <div class="absolute inset-0 rounded-2xl bg-cyan-500/20 blur-md animate-pulse"></div>
          <img
            src="/icons/vitarecord-logo.png"
            alt="VitaRecord"
            class="relative w-16 h-16 rounded-2xl bg-white shadow-md p-1 border border-slate-100 object-contain"
          />
        </div>
        <div class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-cyan-100/80 text-cyan-800 text-2xs font-bold uppercase tracking-wider mb-1">
          <q-icon name="medical_services" size="13px" color="cyan-9" />
          <span>Personal Clínico & Médicos</span>
        </div>
        <h1 class="text-2xl font-black text-slate-900 tracking-tight">
          VitaRecord Clínico
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Acceso para Médicos Especialistas, Recepción y Administradores de Clínica
        </p>
      </div>

      <!-- Formulario de Acceso -->
      <q-card-section class="px-6 py-5 space-y-4">
        <q-form class="space-y-4" @submit.prevent="onSubmit">
          <div>
            <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              Correo Institucional o Médico
            </label>
            <q-input
              v-model="email"
              type="email"
              placeholder="tu.correo@clinica.com"
              outlined
              dense
              class="rounded-xl"
              required
            >
              <template v-slot:prepend>
                <q-icon name="mail_outline" size="18px" color="cyan-8" />
              </template>
            </q-input>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide">
                Contraseña
              </label>
              <router-link
                to="/clinic/forgot-password"
                class="text-xs font-semibold text-cyan-700 hover:text-cyan-900 hover:underline"
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
                <q-icon name="lock_outline" size="18px" color="cyan-8" />
              </template>
            </q-input>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-500 mb-1">
              Código de Segundo Factor MFA (opcional)
            </label>
            <q-input
              v-model="mfaCode"
              placeholder="6 dígitos de tu app autenticadora"
              outlined
              dense
              class="rounded-xl"
            >
              <template v-slot:prepend>
                <q-icon name="security" size="18px" color="cyan-8" />
              </template>
            </q-input>
          </div>

          <q-banner v-if="errorMessage" class="bg-red-50 text-red-800 rounded-xl text-xs border border-red-200">
            <template v-slot:avatar>
              <q-icon name="error_outline" color="red" />
            </template>
            {{ errorMessage }}
          </q-banner>

          <q-btn
            type="submit"
            color="cyan-9"
            label="Ingresar al Sistema Clínico"
            icon-right="arrow_forward"
            :loading="loading"
            class="full-width py-2.5 rounded-xl font-bold shadow-lg shadow-cyan-800/20 text-white tracking-wide"
            no-caps
          />
        </q-form>

        <!-- Accesos directos para pruebas locales de staff -->
        <div class="pt-3 border-t border-slate-100 text-caption">
          <div class="text-2xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            Perfiles de prueba clínica:
          </div>
          <div class="grid grid-cols-3 gap-1.5">
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-sky-50 text-sky-700 border border-sky-200/60 hover:bg-sky-100 transition-colors"
              @click="fillCreds('clinic.admin@intimasalud.com')"
            >
              Admin Clínica
            </button>
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-teal-50 text-teal-700 border border-teal-200/60 hover:bg-teal-100 transition-colors"
              @click="fillCreds('doctor@intimasalud.com')"
            >
              Médico
            </button>
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-amber-50 text-amber-800 border border-amber-200/60 hover:bg-amber-100 transition-colors"
              @click="fillCreds('recepcion@intimasalud.com')"
            >
              Recepción
            </button>
          </div>
        </div>

        <!-- Enlaces cruzados hacia los otros portales -->
        <div class="pt-3 border-t border-slate-100 text-center space-y-1.5 text-xs text-slate-500">
          <div>
            ¿Eres paciente y buscas tus citas?
            <router-link to="/patient/login" class="text-teal-700 font-bold hover:underline ml-1">
              Portal de Pacientes
            </router-link>
          </div>
          <div>
            ¿Superadministrador del sistema?
            <router-link to="/admin/login" class="text-slate-600 font-semibold hover:underline ml-1">
              Portal Super Administrador
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
const loading = ref(false)
const errorMessage = ref('')

const router = useRouter()
const { isLoggedIn } = useAcl()

const ALLOWED_STAFF_ROLES = ['CLINIC_ADMIN', 'DOCTOR', 'RECEPTIONIST']

onMounted(() => {
  if (isLoggedIn.value) {
    router.replace({ name: 'home' })
  }
})

function checkClinicStaffRoleAndRedirect (accessToken, refreshToken) {
  const payload = getValidTokenPayload(accessToken)
  if (!payload || !ALLOWED_STAFF_ROLES.includes(payload.role)) {
    clearAuthToken()
    if (payload?.role === 'PATIENT') {
      errorMessage.value = 'Acceso denegado: Tu cuenta pertenece al portal de pacientes. Por favor ingresa por el Portal de Pacientes.'
    } else if (payload?.role === 'SUPERADMIN' || payload?.role === 'COMPLIANCE_REVIEWER') {
      errorMessage.value = 'Acceso restringido: Las credenciales de administración global deben iniciar sesión en el Portal Super Administrador.'
    } else {
      errorMessage.value = 'Acceso no autorizado: Este portal es exclusivo para médicos, administradores de clínica y recepción.'
    }
    return false
  }

  setAuthToken(accessToken, refreshToken)
  const redirectPath = router.currentRoute.value.query?.redirect
  if (redirectPath) {
    router.push(redirectPath)
  } else {
    router.push({ name: 'home' })
  }
  return true
}

function fillCreds (userEmail) {
  email.value = userEmail
  password.value = 'Password123!'
  mfaCode.value = ''
  errorMessage.value = ''
}

async function onSubmit () {
  loading.value = true
  errorMessage.value = ''
  try {
    const form = new URLSearchParams()
    form.set('username', email.value)
    form.set('password', password.value)
    if (mfaCode.value) form.set('mfa_code', mfaCode.value)

    const { data } = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    checkClinicStaffRoleAndRedirect(data.access_token, data.refresh_token)
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Credenciales inválidas o acceso no autorizado'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.medical-grid {
  background-size: 40px 40px;
  background-image:
    linear-gradient(to right, rgba(8, 145, 178, 0.08) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(8, 145, 178, 0.08) 1px, transparent 1px);
}

.med-float {
  position: absolute;
}

.float-1 {
  top: 18%;
  right: 12%;
  animation: float-slow 8s ease-in-out infinite;
}

.float-2 {
  bottom: 22%;
  left: 10%;
  animation: float-slow 10s ease-in-out infinite 1s;
}

@keyframes float-slow {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(4deg);
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
