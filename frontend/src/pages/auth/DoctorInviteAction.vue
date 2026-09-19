<template>
  <q-page class="flex items-center justify-center p-4 bg-slate-50 min-h-screen">
    <div class="max-w-lg w-full bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
      <!-- Header con gradiente médico -->
      <div class="bg-gradient-to-r from-teal-600 to-cyan-700 p-6 text-white text-center">
        <div class="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-3 backdrop-blur-sm">
          <q-icon name="medical_services" size="32px" class="text-white" />
        </div>
        <h1 class="text-2xl font-bold tracking-tight">Invitación de Afiliación Médica</h1>
        <p class="text-teal-100 text-sm mt-1">Plataforma de Salud ÍntimaSalud</p>
      </div>

      <div class="p-6">
        <!-- Estado de carga -->
        <div v-if="loadingValidation" class="text-center py-10">
          <q-spinner-dots color="primary" size="50px" />
          <p class="text-slate-500 mt-4 text-sm font-medium">Validando token de invitación...</p>
        </div>

        <!-- Error al validar token -->
        <div v-else-if="validationError" class="py-6 text-center">
          <div class="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-3">
            <q-icon name="error_outline" size="28px" />
          </div>
          <h3 class="text-lg font-semibold text-slate-800">Invitación No Válida</h3>
          <p class="text-slate-600 text-sm mt-2 max-w-sm mx-auto">{{ validationError }}</p>
          <q-btn to="/clinic/login" outline color="primary" label="Ir al Inicio de Sesión" class="mt-6 font-medium" />
        </div>

        <!-- Invitación válida lista para responder -->
        <div v-else-if="!responded">
          <div class="bg-slate-50 rounded-xl p-4 border border-slate-200 mb-6 space-y-2">
            <div class="flex items-center text-sm text-slate-600">
              <q-icon name="local_hospital" class="mr-2 text-teal-600" size="18px" />
              <span>Clínica Solicitante:</span>
              <strong class="ml-auto text-slate-800">{{ inviteData.clinic_name }}</strong>
            </div>
            <div class="flex items-center text-sm text-slate-600">
              <q-icon name="badge" class="mr-2 text-teal-600" size="18px" />
              <span>Médico Invitado:</span>
              <strong class="ml-auto text-slate-800">{{ inviteData.doctor_email }}</strong>
            </div>
          </div>

          <p class="text-slate-600 text-sm leading-relaxed mb-6">
            Al aceptar esta vinculación, tu perfil médico quedará afiliado a la plantilla de <strong>{{ inviteData.clinic_name }}</strong>.
            La secretaría y la administración de la clínica recibirán confirmación inmediata de tu respuesta.
          </p>

          <div v-if="actionError" class="p-3 mb-4 rounded-lg bg-red-50 text-red-700 text-sm flex items-center">
            <q-icon name="warning" class="mr-2" size="18px" />
            <span>{{ actionError }}</span>
          </div>

          <div class="space-y-3">
            <q-btn
              color="primary"
              label="Aceptar Afiliación a la Clínica"
              icon="check_circle"
              class="w-full py-2.5 font-semibold text-base shadow-md hover:shadow-lg transition-all"
              no-caps
              :loading="submitting"
              @click="handleResponse('ACCEPT')"
            />
            <q-btn
              outline
              color="negative"
              label="Rechazar Invitación"
              icon="cancel"
              class="w-full py-2 text-sm font-medium"
              no-caps
              :disable="submitting"
              @click="handleResponse('REJECT')"
            />
          </div>
        </div>

        <!-- Pantalla de confirmación tras responder -->
        <div v-else class="text-center py-6">
          <div
            class="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
            :class="lastAction === 'ACCEPT' ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'"
          >
            <q-icon :name="lastAction === 'ACCEPT' ? 'verified' : 'info'" size="36px" />
          </div>
          <h2 class="text-xl font-bold text-slate-800">
            {{ lastAction === 'ACCEPT' ? '¡Afiliación Aceptada!' : 'Invitación Rechazada' }}
          </h2>
          <p class="text-slate-600 text-sm mt-2">
            {{ responseMessage }}
          </p>
          <div class="mt-8">
            <q-btn to="/clinic/login" color="primary" label="Ir a Mi Cuenta" no-caps class="px-6 font-semibold" />
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'boot/axios'

const route = useRoute()
const token = ref('')

const loadingValidation = ref(true)
const validationError = ref('')
const inviteData = ref(null)

const submitting = ref(false)
const actionError = ref('')
const responded = ref(false)
const lastAction = ref('')
const responseMessage = ref('')

onMounted(async () => {
  token.value = route.query.token || ''
  if (!token.value) {
    validationError.value = 'No se proporcionó ningún token de invitación.'
    loadingValidation.value = false
    return
  }

  try {
    const { data } = await api.get(`/invitations/validate?token=${token.value}`)
    inviteData.value = data
  } catch (err) {
    validationError.value = err.response?.data?.detail || 'El enlace de invitación no es válido o ha expirado.'
  } finally {
    loadingValidation.value = false
  }
})

async function handleResponse(action) {
  submitting.value = true
  actionError.value = ''
  try {
    const { data } = await api.post('/invitations/respond', {
      token: token.value,
      action: action
    })
    lastAction.value = action
    responseMessage.value = data.message || 'Respuesta registrada correctamente.'
    responded.value = true
  } catch (err) {
    actionError.value = err.response?.data?.detail || 'No se pudo procesar la respuesta. Intenta nuevamente.'
  } finally {
    submitting.value = false
  }
}
</script>
