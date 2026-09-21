<template>
  <q-page class="flex items-center justify-center p-4 bg-slate-50 min-h-screen">
    <div class="max-w-xl w-full bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
      <!-- Header -->
      <div class="bg-gradient-to-r from-blue-700 to-indigo-800 p-6 text-white text-center">
        <div class="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-3 backdrop-blur-sm">
          <q-icon name="person_add" size="32px" class="text-white" />
        </div>
        <h1 class="text-2xl font-bold tracking-tight">Onboarding de Nuevo Profesional</h1>
        <p class="text-blue-100 text-sm mt-1">Alta y Vinculación Médica - ÍntimaSalud</p>
      </div>

      <div class="p-6">
        <!-- Estado de carga -->
        <div v-if="loadingValidation" class="text-center py-10">
          <q-spinner-dots color="primary" size="50px" />
          <p class="text-slate-500 mt-4 text-sm font-medium">Validando token de registro...</p>
        </div>

        <!-- Error al validar token -->
        <div v-else-if="validationError" class="py-6 text-center">
          <div class="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-3">
            <q-icon name="error_outline" size="28px" />
          </div>
          <h3 class="text-lg font-semibold text-slate-800">Enlace No Válido</h3>
          <p class="text-slate-600 text-sm mt-2 max-w-sm mx-auto">{{ validationError }}</p>
          <q-btn to="/clinic/login" outline color="primary" label="Ir al Inicio de Sesión" class="mt-6 font-medium" />
        </div>

        <!-- Formulario Wizard -->
        <div v-else-if="!completed">
          <!-- Stepper Indicator -->
          <div class="flex items-center justify-between mb-8 px-4">
            <div class="flex items-center">
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all"
                :class="currentStep >= 1 ? 'bg-primary text-white' : 'bg-slate-200 text-slate-500'"
              >
                1
              </div>
              <span class="ml-2 text-xs font-medium text-slate-700 hidden sm:inline">Credenciales</span>
            </div>
            <div class="flex-1 h-0.5 mx-3 bg-slate-200" :class="{ 'bg-primary': currentStep > 1 }"></div>
            <div class="flex items-center">
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all"
                :class="currentStep >= 2 ? 'bg-primary text-white' : 'bg-slate-200 text-slate-500'"
              >
                2
              </div>
              <span class="ml-2 text-xs font-medium text-slate-700 hidden sm:inline">Perfil Profesional</span>
            </div>
            <div class="flex-1 h-0.5 mx-3 bg-slate-200" :class="{ 'bg-primary': currentStep >= 3 }"></div>
            <div class="flex items-center">
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all"
                :class="currentStep >= 3 ? 'bg-primary text-white' : 'bg-slate-200 text-slate-500'"
              >
                3
              </div>
              <span class="ml-2 text-xs font-medium text-slate-700 hidden sm:inline">Confirmación</span>
            </div>
          </div>

          <div class="bg-blue-50/70 border border-blue-100 rounded-xl p-3 mb-6 text-xs text-blue-800 flex items-center">
            <q-icon name="apartment" size="18px" class="mr-2 text-blue-600" />
            <span>Invitación para afiliarse a: <strong>{{ inviteData.clinic_name }}</strong></span>
          </div>

          <!-- Paso 1: Credenciales -->
          <div v-show="currentStep === 1" class="space-y-4">
            <h3 class="text-base font-semibold text-slate-800">Paso 1: Define tu Contraseña de Acceso</h3>
            <p class="text-xs text-slate-500">Crea una contraseña segura para tu cuenta médica asociada a <strong>{{ inviteData.doctor_email }}</strong>.</p>

            <q-input
              v-model="password"
              type="password"
              label="Nueva Contraseña"
              filled
              hint="Mínimo 8 caracteres"
            />
            <q-input
              v-model="confirmPassword"
              type="password"
              label="Confirmar Contraseña"
              filled
              :error="passwordMismatch"
              error-message="Las contraseñas no coinciden"
            />

            <div class="pt-4 flex justify-end">
              <q-btn
                color="primary"
                label="Siguiente: Perfil"
                icon-right="arrow_forward"
                no-caps
                :disable="!canProceedStep1"
                @click="currentStep = 2"
              />
            </div>
          </div>

          <!-- Paso 2: Perfil Profesional -->
          <div v-show="currentStep === 2" class="space-y-4">
            <h3 class="text-base font-semibold text-slate-800">Paso 2: Datos Profesionales</h3>
            <p class="text-xs text-slate-500">Esta información se utilizará para registrar tu colegiatura y agendar consultas.</p>

            <q-input
              v-model="fullName"
              label="Nombre Completo con Título (ej. Dra. Claudia Pérez)"
              filled
              required
            />
            <q-select
              v-model="specialties"
              :options="MEDICAL_SPECIALTIES"
              label="Especialidades Médicas *"
              filled
              multiple
              use-chips
              emit-value
              map-options
              hint="Selecciona una o más especialidades médicas autorizadas"
              :rules="[val => (val && val.length > 0) || 'Selecciona al menos una especialidad']"
            />
            <q-input
              v-model="licenseNumber"
              label="Número de Matrícula / Colegiatura Médica (ej. MP-12345)"
              filled
              required
            />
            <q-input
              v-model="biography"
              type="textarea"
              rows="3"
              label="Breve Resumen / Biografía Profesional"
              filled
            />

            <div class="pt-4 flex justify-between">
              <q-btn flat color="slate-600" label="Atrás" icon="arrow_back" no-caps @click="currentStep = 1" />
              <q-btn
                color="primary"
                label="Siguiente: Confirmar"
                icon-right="arrow_forward"
                no-caps
                :disable="!canProceedStep2"
                @click="currentStep = 3"
              />
            </div>
          </div>

          <!-- Paso 3: Confirmación y Envío -->
          <div v-show="currentStep === 3" class="space-y-4">
            <h3 class="text-base font-semibold text-slate-800">Paso 3: Confirmación y Vinculación</h3>
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 text-sm space-y-2">
              <div><span class="text-slate-500">Médico:</span> <strong>{{ fullName }}</strong></div>
              <div><span class="text-slate-500">Email:</span> <strong>{{ inviteData.doctor_email }}</strong></div>
              <div>
                <span class="text-slate-500">Especialidades:</span>
                <div class="flex flex-wrap gap-1 mt-1">
                  <q-badge
                    v-for="sp in specialties"
                    :key="sp"
                    color="primary"
                    text-color="white"
                    class="text-xs font-semibold px-2 py-0.5"
                  >
                    {{ sp }}
                  </q-badge>
                </div>
              </div>
              <div><span class="text-slate-500">Matrícula:</span> <strong>{{ licenseNumber }}</strong></div>
              <div><span class="text-slate-500">Clínica:</span> <strong>{{ inviteData.clinic_name }}</strong></div>
            </div>

            <div class="bg-amber-50 border border-amber-200 p-3 rounded-xl text-xs text-amber-900 flex items-start">
              <q-icon name="info" size="18px" class="text-amber-600 mr-2 mt-0.5" />
              <span>
                Conforme a la normativa médica de la plataforma, una vez finalizado el onboarding tu cuenta pasará al estado
                <strong>Pendiente de Verificación</strong> para que el comité de cumplimiento valide tu matrícula profesional antes de habilitar citas públicas.
              </span>
            </div>

            <div v-if="submitError" class="p-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center">
              <q-icon name="warning" class="mr-2" size="18px" />
              <span>{{ submitError }}</span>
            </div>

            <div class="pt-4 flex justify-between">
              <q-btn flat color="slate-600" label="Atrás" icon="arrow_back" no-caps @click="currentStep = 2" />
              <q-btn
                color="primary"
                label="Completar Onboarding"
                icon="done_all"
                no-caps
                :loading="submitting"
                @click="submitOnboarding"
              />
            </div>
          </div>
        </div>

        <!-- Pantalla de éxito final -->
        <div v-else class="text-center py-6">
          <div class="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-4">
            <q-icon name="verified" size="36px" />
          </div>
          <h2 class="text-xl font-bold text-slate-800">¡Onboarding Completado con Éxito!</h2>
          <p class="text-slate-600 text-sm mt-2 max-w-md mx-auto">
            Tu cuenta y perfil médico han sido dados de alta. La administración de <strong>{{ inviteData.clinic_name }}</strong> y el equipo de cumplimiento han sido notificados.
          </p>
          <div class="mt-8">
            <q-btn to="/clinic/login" color="primary" label="Iniciar Sesión" no-caps class="px-8 font-semibold" />
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
import { MEDICAL_SPECIALTIES } from 'src/constants/specialties'

const route = useRoute()
const token = ref('')

const loadingValidation = ref(true)
const validationError = ref('')
const inviteData = ref(null)

const currentStep = ref(1)
const password = ref('')
const confirmPassword = ref('')
const fullName = ref('')
const specialties = ref([])
const licenseNumber = ref('')
const biography = ref('')

const submitting = ref(false)
const submitError = ref('')
const completed = ref(false)

const passwordMismatch = computed(() => {
  return confirmPassword.value.length > 0 && password.value !== confirmPassword.value
})

const canProceedStep1 = computed(() => {
  return password.value.length >= 8 && password.value === confirmPassword.value
})

const canProceedStep2 = computed(() => {
  return fullName.value.trim().length > 0 && specialties.value.length > 0 && licenseNumber.value.trim().length > 0
})

onMounted(async () => {
  token.value = route.query.token || ''
  if (!token.value) {
    validationError.value = 'No se proporcionó ningún token de registro.'
    loadingValidation.value = false
    return
  }

  try {
    const { data } = await api.get(`/invitations/validate?token=${token.value}`)
    inviteData.value = data
    if (data.full_name && !fullName.value) {
      fullName.value = data.full_name
    }
    if (data.specialties && Array.isArray(data.specialties) && data.specialties.length > 0) {
      specialties.value = [...data.specialties]
    } else if (data.specialty) {
      specialties.value = data.specialty.split(',').map(s => s.trim()).filter(Boolean)
    }
  } catch (err) {
    validationError.value = err.response?.data?.detail || 'El enlace de onboarding no es válido o ha expirado.'
  } finally {
    loadingValidation.value = false
  }
})

async function submitOnboarding() {
  submitting.value = true
  submitError.value = ''
  try {
    await api.post('/invitations/onboarding', {
      token: token.value,
      password: password.value,
      full_name: fullName.value,
      specialty: specialties.value.join(', '),
      specialties: specialties.value,
      license_number: licenseNumber.value,
      biography: biography.value
    })
    completed.value = true
  } catch (err) {
    submitError.value = err.response?.data?.detail || 'No se pudo completar el onboarding.'
  } finally {
    submitting.value = false
  }
}
</script>
