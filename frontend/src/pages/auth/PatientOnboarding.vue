<template>
  <q-page class="flex items-center justify-center p-4 min-h-screen bg-slate-50">
    <div class="max-w-md w-full bg-white rounded-3xl shadow-xl overflow-hidden border border-slate-200">
      <!-- Cabecera Institucional VitaRecord -->
      <div class="bg-gradient-to-r from-teal-700 via-cyan-700 to-blue-800 p-8 text-white text-center">
        <div class="w-16 h-16 bg-white/15 rounded-2xl flex items-center justify-center mx-auto mb-3 backdrop-blur-md shadow-inner">
          <img src="/icons/vitarecord-logo.png" alt="VitaRecord" class="w-10 h-10 object-contain drop-shadow" />
        </div>
        <h1 class="text-2xl font-black tracking-tight">VitaRecord</h1>
        <p class="text-teal-100 text-xs mt-1 font-medium">Activación de Cuenta de Paciente</p>
      </div>

      <div class="p-6 md:p-8">
        <!-- Estado 1: Validando token -->
        <div v-if="loadingValidation" class="text-center py-10 space-y-3">
          <q-spinner-dots color="teal" size="48px" />
          <p class="text-slate-500 text-xs font-medium">Verificando invitación médica...</p>
        </div>

        <!-- Estado 2: Error de token -->
        <div v-else-if="validationError" class="py-6 text-center space-y-4">
          <div class="w-14 h-14 rounded-full bg-red-50 text-red-600 flex items-center justify-center mx-auto">
            <q-icon name="error_outline" size="32px" />
          </div>
          <h3 class="text-base font-bold text-slate-800">Enlace No Válido o Expirado</h3>
          <p class="text-slate-600 text-xs max-w-xs mx-auto leading-relaxed">{{ validationError }}</p>
          <q-btn
            to="/login"
            outline
            color="primary"
            label="Ir a Iniciar Sesión"
            no-caps
            class="font-semibold"
          />
        </div>

        <!-- Estado 3: Formulario de Registro de Clave -->
        <div v-else-if="!completed" class="space-y-5">
          <!-- Resumen de la cita confirmada -->
          <div class="bg-teal-50/70 border border-teal-200/80 rounded-2xl p-4 text-xs text-teal-950 space-y-2">
            <div class="flex items-center text-teal-700 font-bold">
              <q-icon name="verified" size="18px" class="mr-1.5 text-teal-600" />
              <span>¡Cita Médica Confirmada!</span>
            </div>
            <p class="text-slate-700 leading-relaxed">
              Hola <strong>{{ inviteData.full_name || inviteData.email }}</strong>, el especialista ha aceptado tu consulta médica:
            </p>
            <div class="bg-white p-3 rounded-xl border border-teal-100 space-y-1">
              <div v-if="inviteData.doctor_name" class="font-bold text-slate-800">
                {{ inviteData.doctor_name }}
              </div>
              <div v-if="inviteData.clinic_name" class="text-slate-500 flex items-center">
                <q-icon name="apartment" size="13px" class="mr-1 text-teal-600" />
                {{ inviteData.clinic_name }}
              </div>
              <div v-if="inviteData.start_time" class="text-teal-700 font-semibold flex items-center">
                <q-icon name="event" size="13px" class="mr-1 text-teal-600" />
                {{ inviteData.start_time }}
              </div>
            </div>
          </div>

          <div class="space-y-1">
            <h2 class="text-sm font-bold text-slate-800">Crea tu Contraseña de Acceso</h2>
            <p class="text-2xs text-slate-500">
              Con esta contraseña podrás ingresar a VitaRecord para ver tu cita, descargar tus recetas médicas electrónicas con código QR, ver tu historia clínica e informes de resultados.
            </p>
          </div>

          <form @submit.prevent="submitOnboarding" class="space-y-4">
            <q-input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              label="Nueva Contraseña"
              outlined
              dense
              hint="Mínimo 8 caracteres"
              :rules="[val => !!val && val.length >= 8 || 'Mínimo 8 caracteres']"
            >
              <template #append>
                <q-icon
                  :name="showPassword ? 'visibility_off' : 'visibility'"
                  class="cursor-pointer text-slate-400"
                  @click="showPassword = !showPassword"
                />
              </template>
            </q-input>

            <q-input
              v-model="confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              label="Confirmar Contraseña"
              outlined
              dense
              :error="passwordMismatch"
              error-message="Las contraseñas no coinciden"
            />

            <q-btn
              type="submit"
              color="teal-8"
              label="Activar Mi Cuenta y Entrar"
              icon-right="arrow_forward"
              no-caps
              unelevated
              :loading="submitting"
              :disable="!canSubmit"
              class="w-full py-2.5 font-bold rounded-xl shadow-md text-sm mt-2"
            />
          </form>
        </div>

        <!-- Estado 4: Completado exitosamente -->
        <div v-else class="py-8 text-center space-y-4">
          <div class="w-16 h-16 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center mx-auto shadow-xs">
            <q-icon name="check_circle" size="38px" />
          </div>
          <h2 class="text-lg font-bold text-slate-800">¡Cuenta Activada con Éxito!</h2>
          <p class="text-xs text-slate-500 max-w-xs mx-auto">
            Bienvenido/a a VitaRecord. Tu contraseña ha sido establecida y ya tienes acceso directo a tus citas médicas y expedientes clínicos.
          </p>
          <div class="flex items-center justify-center text-2xs text-teal-700 font-semibold space-x-2 animate-pulse pt-2">
            <q-spinner-dots size="18px" />
            <span>Ingresando al sistema de pacientes...</span>
          </div>
          <div class="pt-2">
            <q-btn
              to="/appointments/my-list"
              color="teal-8"
              label="Ir al Portal de Pacientes Ahora"
              icon-right="arrow_forward"
              no-caps
              class="font-bold px-6 py-2 rounded-xl shadow-sm"
            />
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Notify } from 'quasar'
import { api } from 'boot/axios'
import { setAuthToken } from 'src/composables/useAcl'

const route = useRoute()
const router = useRouter()

const loadingValidation = ref(true)
const validationError = ref('')
const submitting = ref(false)
const completed = ref(false)

const inviteData = ref({
  email: '',
  full_name: '',
  doctor_name: '',
  clinic_name: '',
  appointment_id: '',
  start_time: ''
})

const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)

const passwordMismatch = computed(() => {
  return confirmPassword.value && password.value !== confirmPassword.value
})

const canSubmit = computed(() => {
  return password.value.length >= 8 && password.value === confirmPassword.value
})

onMounted(async () => {
  const token = route.query.token
  if (!token) {
    loadingValidation.value = false
    validationError.value = 'No se proporcionó un enlace de activación válido.'
    return
  }

  try {
    const { data } = await api.get('/auth/patient-onboarding/validate', {
      params: { token }
    })
    inviteData.value = data
  } catch (err) {
    validationError.value = err.response?.data?.detail || 'El enlace de activación ha expirado o no es válido.'
  } finally {
    loadingValidation.value = false
  }
})

async function submitOnboarding () {
  if (!canSubmit.value) return
  submitting.value = true

  try {
    const token = route.query.token
    const { data } = await api.post('/auth/patient-onboarding/complete', {
      token,
      password: password.value
    })

    // Guardar tokens y sincronizar estado de autenticación en Axios y useAcl
    if (data.access_token) {
      setAuthToken(data.access_token, data.refresh_token)
    }

    Notify.create({
      type: 'positive',
      message: '¡Tu cuenta ha sido activada con éxito! Bienvenido/a al portal de pacientes de VitaRecord.',
      icon: 'verified',
      timeout: 4000
    })

    completed.value = true
    setTimeout(() => {
      router.push('/appointments/my-list')
    }, 1400)
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al completar el registro.'
    })
  } finally {
    submitting.value = false
  }
}
</script>
