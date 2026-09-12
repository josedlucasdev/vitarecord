<template>
  <q-dialog v-model="showModal" persistent>
    <q-card style="width: 550px; max-width: 95vw;" class="rounded-borders">
      <!-- Encabezado de Emergencia -->
      <q-card-section class="bg-negative text-white row items-center q-pb-sm">
        <q-icon name="emergency" size="md" class="q-mr-sm" />
        <div class="text-h6 text-weight-bold">Urgencia Médica Remota (SOS)</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup :disable="isDispatching" />
      </q-card-section>

      <!-- Pantalla Activa: Radar en Vivo de la Emergencia -->
      <q-card-section v-if="activeIncident" class="q-pa-md text-center">
        <div class="q-py-md">
          <q-spinner-puff v-if="activeIncident.status !== 'RESOLVED'" color="negative" size="80px" />
          <q-icon v-else name="check_circle" color="positive" size="80px" />
        </div>

        <div class="text-h6 text-weight-bold q-mb-xs">
          {{ statusLabel(activeIncident.status) }}
        </div>
        <div class="text-caption text-grey-7 q-mb-md">
          Incidente #{{ activeIncident.id.slice(0, 8) }} | Nivel de Escalamiento: {{ activeIncident.escalation_level }}
        </div>

        <q-banner rounded class="bg-red-1 text-negative q-mb-md text-left" dense>
          <template v-slot:avatar>
            <q-icon name="report_problem" color="negative" />
          </template>
          <b>Motivo:</b> {{ activeIncident.chief_complaint }}
        </q-banner>

        <!-- Datos del Médico si fue asignado -->
        <div v-if="activeIncident.doctor_name" class="q-pa-sm bg-green-1 rounded-borders text-positive text-weight-bold q-mb-md">
          <q-icon name="medical_services" class="q-mr-xs" />
          Médico a Cargo: {{ activeIncident.doctor_name }}
          <div v-if="activeIncident.response_time_seconds" class="text-caption text-grey-8">
            Atendido en SLA: {{ Math.round(activeIncident.response_time_seconds) }} segundos
          </div>
        </div>

        <!-- Notas de Triaje si está resuelto -->
        <div v-if="activeIncident.triage_notes" class="q-pa-sm bg-grey-2 rounded-borders text-left q-mb-md">
          <div class="text-caption text-weight-bold">Notas de Triaje Clínico:</div>
          <div>{{ activeIncident.triage_notes }}</div>
        </div>

        <div class="row q-gutter-sm justify-center q-mt-md">
          <q-btn
            icon="call"
            label="Llamar 911 Directo"
            color="negative"
            outline
            href="tel:911"
          />
          <q-btn
            v-if="activeIncident.status === 'RESOLVED'"
            label="Cerrar y Salir"
            color="primary"
            v-close-popup
            @click="resetForm"
          />
        </div>
      </q-card-section>

      <!-- Pantalla Inicial: Formulario con Descargo Obligatorio -->
      <q-card-section v-else class="q-pa-md">
        <!-- Banner de Descargo Legal 911 -->
        <q-banner rounded class="bg-red-1 text-negative q-mb-md border-negative">
          <template v-slot:avatar>
            <q-icon name="warning" color="negative" size="md" />
          </template>
          <div class="text-subtitle2 text-weight-bold q-mb-xs">DESCARGO LEGAL DE RESPONSABILIDAD:</div>
          <div class="text-caption">
            Este botón activa tele-orientación médica de guardia para contingencias.
            <b>NO SUSTITUYE EL SERVICIO OFICIAL DE EMERGENCIAS (911)</b> ni traslados de soporte vital avanzado en ambulancia.
          </div>
          <div class="q-mt-sm">
            <q-btn
              label="Llamar al 911 Inmediatamente"
              icon="phone_in_talk"
              color="negative"
              size="sm"
              unelevated
              href="tel:911"
            />
          </div>
        </q-banner>

        <!-- Descripción del Síntoma -->
        <q-input
          v-model="chiefComplaint"
          type="textarea"
          rows="3"
          label="¿Cuál es la urgencia médica o síntoma crítico? *"
          outlined
          dense
          placeholder="Ej. Dolor abdominal intenso, hemorragia aguda, dificultad respiratoria..."
          class="q-mb-sm"
        />

        <!-- Ubicación GPS -->
        <div class="row items-center q-mb-md q-gutter-sm">
          <q-btn
            icon="my_location"
            :label="locationCaptured ? 'Ubicación GPS Detectada' : 'Detectar Mi Ubicación GPS'"
            :color="locationCaptured ? 'positive' : 'grey-7'"
            outline
            size="sm"
            @click="captureLocation"
            :loading="detectingLocation"
          />
          <div v-if="locationCaptured" class="text-caption text-grey-8">
            Lat: {{ latitude?.toFixed(4) }}, Lng: {{ longitude?.toFixed(4) }}
          </div>
        </div>

        <!-- Checkbox de Descargo Obligatorio -->
        <q-checkbox
          v-model="disclaimerAcknowledged"
          color="negative"
          keep-color
          class="text-weight-medium q-mb-sm"
        >
          <span class="text-caption">
            He leído y acepto que este canal es de orientación remota y confirmo el disparo del protocolo SOS.
          </span>
        </q-checkbox>
      </q-card-section>

      <!-- Acciones de Disparo -->
      <q-card-actions v-if="!activeIncident" align="right" class="q-px-md q-pb-md">
        <q-btn flat label="Cancelar" color="grey-7" v-close-popup />
        <q-btn
          color="negative"
          icon="emergency_share"
          label="ACTIVAR ALERTA SOS"
          unelevated
          :disable="!disclaimerAcknowledged || chiefComplaint.trim().length < 5"
          :loading="isDispatching"
          @click="submitSos"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { api } from 'src/boot/axios'
import { useQuasar } from 'quasar'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const $q = useQuasar()

const showModal = defineModel({ default: false })
const chiefComplaint = ref('')
const disclaimerAcknowledged = ref(false)
const latitude = ref(null)
const longitude = ref(null)
const locationCaptured = ref(false)
const detectingLocation = ref(false)
const isDispatching = ref(false)
const activeIncident = ref(null)

function captureLocation () {
  if (!navigator.geolocation) {
    $q.notify({ type: 'warning', message: 'Geolocalización no soportada en su navegador.' })
    return
  }
  detectingLocation.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      latitude.value = pos.coords.latitude
      longitude.value = pos.coords.longitude
      locationCaptured.value = true
      detectingLocation.value = false
      $q.notify({ type: 'positive', message: 'Ubicación GPS capturada con éxito.' })
    },
    (err) => {
      detectingLocation.value = false
      $q.notify({ type: 'warning', message: 'No se pudo obtener la ubicación: ' + err.message })
    },
    { timeout: 8000 }
  )
}

async function submitSos () {
  if (!disclaimerAcknowledged.value) {
    $q.notify({ type: 'negative', message: 'Debe aceptar el descargo legal para activar SOS.' })
    return
  }

  isDispatching.value = true
  try {
    const payload = {
      disclaimer_acknowledged: true,
      chief_complaint: chiefComplaint.value.trim(),
      latitude: latitude.value,
      longitude: longitude.value
    }
    const { data } = await api.post('/emergencies/sos', payload)
    activeIncident.value = data
    $q.notify({
      type: 'positive',
      icon: 'emergency',
      message: '¡Alerta SOS activada! Protocolo de tele-orientación médica iniciado.',
      position: 'top'
    })
  } catch (err) {
    const detail = err.response?.data?.detail || 'Error al activar protocolo SOS.'
    $q.notify({ type: 'negative', message: detail })
  } finally {
    isDispatching.value = false
  }
}

function resetForm () {
  chiefComplaint.value = ''
  disclaimerAcknowledged.value = false
  locationCaptured.value = false
  latitude.value = null
  longitude.value = null
  activeIncident.value = null
}

function statusLabel (status) {
  switch (status) {
    case 'TRIGGERED':
    case 'DISPATCHED':
      return 'Buscando Médico de Guardia en Turno...'
    case 'ESCALATED_DOCTOR_2':
      return 'Escalando a Médico Secundario...'
    case 'ESCALATED_MODERATOR':
      return 'Intervención de Torre de Control y Moderación...'
    case 'ESCALATED_BACKUP':
      return 'Alerta Crítica: Despacho a Línea de Contingencia...'
    case 'ACCEPTED':
      return 'Médico Asignado - En Atención'
    case 'RESOLVED':
      return 'Incidente Resuelto'
    default:
      return status
  }
}
</script>

<style scoped>
.border-negative {
  border: 1px solid #c10015;
}
</style>
