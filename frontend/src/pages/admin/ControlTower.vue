<template>
  <q-page class="q-pa-md bg-grey-1">
    <!-- Header de la Torre de Control -->
    <div class="row items-center justify-between q-mb-md">
      <div>
        <div class="text-h5 text-weight-bolder text-primary row items-center">
          <q-icon name="radar" color="negative" size="md" class="q-mr-sm" />
          Torre de Control 360°
          <q-badge
            :color="wsConnected ? 'positive' : 'negative'"
            class="q-ml-md"
            align="middle"
          >
            {{ wsConnected ? 'EN VIVO (WS ACTIVO)' : 'DESCONECTADO' }}
          </q-badge>
        </div>
        <div class="text-caption text-grey-7">
          Monitoreo multicanal de urgencias médicas, SLA de 2 minutos y cadena de escalamiento.
        </div>
      </div>
      <div class="row q-gutter-sm">
        <q-btn
          icon="refresh"
          label="Actualizar"
          outline
          color="primary"
          dense
          class="q-px-sm"
          :loading="loading"
          @click="loadActiveIncidents"
        />
        <q-btn
          icon="emergency"
          label="Lanzar Test SOS"
          color="negative"
          unelevated
          dense
          class="q-px-sm"
          @click="showSosModal = true"
        />
      </div>
    </div>

    <!-- Tarjetas Resumen de Nivel y SLA -->
    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="bg-blue-1 text-primary flat bordered">
          <q-card-section class="row items-center justify-between">
            <div>
              <div class="text-caption text-weight-bold">NIVEL 1: MÉDICO 1</div>
              <div class="text-h4 text-weight-bolder">{{ countByLevel(1) }}</div>
            </div>
            <q-icon name="local_hospital" size="lg" color="primary" />
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="bg-amber-1 text-amber-9 flat bordered">
          <q-card-section class="row items-center justify-between">
            <div>
              <div class="text-caption text-weight-bold">NIVEL 2: MÉDICO 2</div>
              <div class="text-h4 text-weight-bolder">{{ countByLevel(2) }}</div>
            </div>
            <q-icon name="escalator_warning" size="lg" color="amber-9" />
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="bg-deep-orange-1 text-deep-orange-9 flat bordered">
          <q-card-section class="row items-center justify-between">
            <div>
              <div class="text-caption text-weight-bold">NIVEL 3: TORRE / MODERACIÓN</div>
              <div class="text-h4 text-weight-bolder">{{ countByLevel(3) }}</div>
            </div>
            <q-icon name="security" size="lg" color="deep-orange-9" />
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="bg-red-1 text-negative flat bordered">
          <q-card-section class="row items-center justify-between">
            <div>
              <div class="text-caption text-weight-bold">NIVEL 4: CONTINGENCIA 911</div>
              <div class="text-h4 text-weight-bolder">{{ countByLevel(4) }}</div>
            </div>
            <q-icon name="phone_in_talk" size="lg" color="negative" />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Tabla de Incidentes Activos -->
    <q-card flat bordered class="rounded-borders">
      <q-table
        :rows="incidents"
        :columns="columns"
        row-key="id"
        :loading="loading"
        no-data-label="No hay urgencias médicas activas en este momento. Torre en calma."
        class="text-left"
      >
        <!-- Nivel y Estado -->
        <template v-slot:body-cell-escalation_level="props">
          <q-td :props="props">
            <q-badge
              :color="levelColor(props.row.escalation_level)"
              class="text-weight-bold q-pa-xs"
            >
              NIVEL {{ props.row.escalation_level }}
            </q-badge>
            <div class="text-caption text-weight-bold q-mt-xs">
              {{ props.row.status }}
            </div>
          </q-td>
        </template>

        <!-- Paciente y Ubicación -->
        <template v-slot:body-cell-patient="props">
          <q-td :props="props">
            <div class="text-weight-bold">{{ props.row.patient_name || 'Paciente ' + props.row.patient_id.slice(0, 8) }}</div>
            <div class="text-caption text-grey-7">
              {{ props.row.clinic_name || 'Sede Central' }}
            </div>
            <div v-if="props.row.latitude" class="text-caption text-primary">
              <q-icon name="place" size="xs" />
              {{ props.row.latitude.toFixed(3) }}, {{ props.row.longitude.toFixed(3) }}
            </div>
          </q-td>
        </template>

        <!-- Motivo Urgente -->
        <template v-slot:body-cell-chief_complaint="props">
          <q-td :props="props" style="max-width: 250px; white-space: normal;">
            <div class="text-body2 text-weight-medium text-negative">
              {{ props.row.chief_complaint }}
            </div>
          </q-td>
        </template>

        <!-- SLA y Antigüedad -->
        <template v-slot:body-cell-sla="props">
          <q-td :props="props">
            <div class="text-caption text-weight-bold">
              Iniciado: {{ formatTime(props.row.triggered_at) }}
            </div>
            <div v-if="props.row.response_time_seconds" class="text-caption text-positive">
              Tomado en: {{ Math.round(props.row.response_time_seconds) }}s
            </div>
            <div v-else class="text-caption text-warning text-weight-bolder">
              Pendiente de toma
            </div>
          </q-td>
        </template>

        <!-- Médico Asignado -->
        <template v-slot:body-cell-assigned_doctor="props">
          <q-td :props="props">
            <div v-if="props.row.doctor_name" class="text-positive text-weight-bold">
              <q-icon name="check_circle" size="xs" />
              {{ props.row.doctor_name }}
            </div>
            <div v-else class="text-grey-6 italic">
              Sin médico asignado
            </div>
          </q-td>
        </template>

        <!-- Acciones Rápidas -->
        <template v-slot:body-cell-actions="props">
          <q-td :props="props" class="q-gutter-xs">
            <!-- Botón de Escalamiento Manual -->
            <q-btn
              icon="arrow_upward"
              label="Escalar"
              size="sm"
              color="deep-orange"
              dense
              unelevated
              @click="escalateIncident(props.row.id)"
              :disable="props.row.status === 'RESOLVED' || props.row.status === 'ACCEPTED'"
            >
              <q-tooltip>Escalar al siguiente nivel en la cadena multicanal</q-tooltip>
            </q-btn>

            <!-- Reconocer (SLA de 2 min del moderador de turno) -->
            <q-btn
              v-if="canMonitor && !props.row.acknowledged_at && ['ESCALATED_MODERATOR', 'ESCALATED_BACKUP'].includes(props.row.status)"
              icon="notifications_active"
              label="Reconocer"
              size="sm"
              color="negative"
              dense
              unelevated
              @click="acknowledgeIncident(props.row.id)"
            >
              <q-tooltip>Confirmar que la Torre está atendiendo el incidente (detiene la llamada a la línea de respaldo)</q-tooltip>
            </q-btn>

            <!-- Asignación manual de médico -->
            <q-btn
              v-if="canMonitor && props.row.status !== 'ACCEPTED' && props.row.status !== 'RESOLVED'"
              icon="person_add"
              label="Asignar"
              size="sm"
              color="teal"
              dense
              unelevated
              @click="openAssignDialog(props.row)"
            >
              <q-tooltip>Asignar manualmente un médico disponible</q-tooltip>
            </q-btn>

            <!-- Botón Médico: Tomar Caso -->
            <q-btn
              v-if="canRespond && props.row.status !== 'ACCEPTED' && props.row.status !== 'RESOLVED'"
              icon="handshake"
              label="Tomar"
              size="sm"
              color="positive"
              dense
              unelevated
              @click="acceptIncident(props.row.id)"
            >
              <q-tooltip>Tomar y atender caso como médico de guardia</q-tooltip>
            </q-btn>

            <!-- Botón Resolver Caso -->
            <q-btn
              v-if="canRespond || canMonitor"
              icon="check"
              label="Resolver"
              size="sm"
              color="primary"
              dense
              unelevated
              @click="openResolveDialog(props.row)"
              :disable="props.row.status === 'RESOLVED'"
            >
              <q-tooltip>Cerrar caso con notas de triaje médico</q-tooltip>
            </q-btn>

            <!-- Botón Ver Auditoría / Timeline -->
            <q-btn
              icon="history"
              label="Auditoría"
              size="sm"
              color="grey-8"
              flat
              dense
              @click="openAuditDialog(props.row.id)"
            >
              <q-tooltip>Ver logs inmutables de notificaciones</q-tooltip>
            </q-btn>
          </q-td>
        </template>
      </q-table>
    </q-card>

    <!-- Diálogo de Resolución de Incidente -->
    <q-dialog v-model="resolveDialog.show">
      <q-card style="width: 500px; max-width: 90vw;">
        <q-card-section class="bg-primary text-white">
          <div class="text-h6">Finalizar Urgencia Médica</div>
          <div class="text-caption">Ingresar notas clínicas de triaje y conducta tomada.</div>
        </q-card-section>
        <q-card-section class="q-pa-md">
          <q-input
            v-model="resolveDialog.triageNotes"
            type="textarea"
            rows="4"
            outlined
            dense
            label="Notas de Triaje Clínico *"
            placeholder="Detallar indicaciones, teleconsulta brindada o derivación a ambulancia/centro médico..."
          />
        </q-card-section>
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="Cancelar" color="grey-7" v-close-popup />
          <q-btn
            color="primary"
            label="Confirmar y Resolver"
            unelevated
            :disable="resolveDialog.triageNotes.trim().length < 5"
            @click="submitResolve"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Diálogo de Asignación Manual de Médico -->
    <q-dialog v-model="assignDialog.show">
      <q-card style="width: 460px; max-width: 95vw;">
        <q-card-section class="bg-teal-8 text-white row items-center">
          <q-icon name="person_add" size="sm" class="q-mr-sm" />
          <div class="text-h6">Asignar médico de guardia</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-select
            v-model="assignDialog.doctorId"
            :options="assignDialog.options"
            option-value="id"
            option-label="label"
            emit-value
            map-options
            outlined
            dense
            :loading="assignDialog.loading"
            label="Médico verificado"
            hint="Primero se muestran los médicos con guardia activa"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" color="grey-7" v-close-popup />
          <q-btn
            unelevated
            color="teal"
            label="Asignar y llamar"
            :disable="!assignDialog.doctorId"
            @click="submitAssign"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Diálogo de Línea de Tiempo y Auditoría -->
    <q-dialog v-model="auditDialog.show">
      <q-card style="width: 600px; max-width: 95vw;">
        <q-card-section class="bg-grey-9 text-white row items-center">
          <q-icon name="history" size="sm" class="q-mr-sm" />
          <div class="text-h6">Auditoría Multicanal del Incidente</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section class="q-pa-md" style="max-height: 60vh; overflow-y: auto;">
          <q-timeline color="primary" dense>
            <q-timeline-entry
              v-for="log in auditDialog.logs"
              :key="log.id"
              :title="log.channel + ' - ' + log.status"
              :subtitle="formatDateTime(log.sent_at)"
              :icon="channelIcon(log.channel)"
              :color="log.status === 'DELIVERED' ? 'positive' : 'primary'"
            >
              <div>{{ log.error_message || 'Intento #' + log.attempt_number }}</div>
              <div v-if="log.response_time_seconds" class="text-caption text-grey-8">
                Tiempo de respuesta: {{ Math.round(log.response_time_seconds) }}s
              </div>
            </q-timeline-entry>
          </q-timeline>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Componente Modal SOS para pruebas directas -->
    <EmergencySosModal v-model="showSosModal" />
  </q-page>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { api } from 'src/boot/axios'
import { getAuthToken, useAcl } from 'src/composables/useAcl'
import { useQuasar } from 'quasar'
import EmergencySosModal from 'src/components/EmergencySosModal.vue'

const $q = useQuasar()
const { can, hasRole } = useAcl()
// El canal en vivo solo difunde a staff global; los admins de sede usan sondeo.
const canUseLiveChannel = computed(() => hasRole('SUPERADMIN', 'MODERATOR', 'COMPLIANCE_REVIEWER'))
let pollTimer = null
let unmounted = false

const canMonitor = computed(() => can('emergency:monitor'))
const canRespond = computed(() => can('emergency:respond'))

const incidents = ref([])
const loading = ref(false)
const wsConnected = ref(false)
let ws = null

const showSosModal = ref(false)

const resolveDialog = reactive({
  show: false,
  incidentId: null,
  triageNotes: ''
})

const assignDialog = reactive({
  show: false,
  incidentId: null,
  doctorId: null,
  options: [],
  loading: false
})

const auditDialog = reactive({
  show: false,
  logs: []
})

const columns = [
  { name: 'escalation_level', label: 'Nivel / Estado', align: 'left', field: 'escalation_level' },
  { name: 'patient', label: 'Paciente & Sede', align: 'left', field: 'patient_name' },
  { name: 'chief_complaint', label: 'Motivo de Urgencia', align: 'left', field: 'chief_complaint' },
  { name: 'sla', label: 'SLA / Horario', align: 'left', field: 'triggered_at' },
  { name: 'assigned_doctor', label: 'Médico a Cargo', align: 'left', field: 'doctor_name' },
  { name: 'actions', label: 'Acciones', align: 'center' }
]

function countByLevel (lvl) {
  return incidents.value.filter(i => i.escalation_level === lvl).length
}

function levelColor (lvl) {
  switch (lvl) {
    case 1: return 'primary'
    case 2: return 'amber-9'
    case 3: return 'deep-orange-9'
    case 4: return 'negative'
    default: return 'grey-7'
  }
}

function channelIcon (ch) {
  switch (ch) {
    case 'PUSH': return 'notifications'
    case 'VOICE_CALL': return 'phone'
    case 'WEBSOCKET': return 'hub'
    case 'WHATSAPP': return 'chat'
    default: return 'send'
  }
}

function formatTime (isoStr) {
  if (!isoStr) return '-'
  return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDateTime (isoStr) {
  if (!isoStr) return '-'
  return new Date(isoStr).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })
}

async function loadActiveIncidents () {
  loading.value = true
  try {
    const { data } = await api.get('/emergencies/active')
    incidents.value = data
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error cargando incidentes activos: ' + (err.response?.data?.detail || err.message) })
  } finally {
    loading.value = false
  }
}

async function escalateIncident (incidentId) {
  try {
    const { data } = await api.post(`/emergencies/${incidentId}/escalate`)
    $q.notify({ type: 'warning', message: `Incidente escalado a Nivel ${data.escalation_level} (${data.status}).` })
    await loadActiveIncidents()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'No se pudo escalar: ' + (err.response?.data?.detail || err.message) })
  }
}

async function acknowledgeIncident (incidentId) {
  try {
    await api.post(`/emergencies/${incidentId}/acknowledge`)
    $q.notify({ type: 'positive', message: 'Incidente reconocido por la Torre de Control.' })
    await loadActiveIncidents()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'No se pudo reconocer: ' + (err.response?.data?.detail || err.message) })
  }
}

async function openAssignDialog (incident) {
  assignDialog.incidentId = incident.id
  assignDialog.doctorId = null
  assignDialog.show = true
  assignDialog.loading = true
  try {
    const { data } = await api.get('/doctors')
    assignDialog.options = [...data]
      .sort((a, b) => Number(!!b.is_available_for_emergencies) - Number(!!a.is_available_for_emergencies))
      .map(d => ({
        id: d.id,
        label: `${d.full_name || d.email}${d.is_available_for_emergencies ? ' · de guardia' : ''}`
      }))
  } catch (err) {
    $q.notify({ type: 'negative', message: 'No se pudo cargar la lista de médicos: ' + (err.response?.data?.detail || err.message) })
  } finally {
    assignDialog.loading = false
  }
}

async function submitAssign () {
  try {
    await api.post(`/emergencies/${assignDialog.incidentId}/assign`, { doctor_id: assignDialog.doctorId })
    assignDialog.show = false
    $q.notify({ type: 'positive', message: 'Médico asignado y notificado (push, WhatsApp y llamada).' })
    await loadActiveIncidents()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'No se pudo asignar: ' + (err.response?.data?.detail || err.message) })
  }
}

// Alerta sonora prioritaria para eventos críticos (plan 2.B.7).
function playAlarm () {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    ;[0, 0.35, 0.7].forEach(offset => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'square'
      osc.frequency.value = 880
      gain.gain.value = 0.15
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(ctx.currentTime + offset)
      osc.stop(ctx.currentTime + offset + 0.2)
    })
    setTimeout(() => ctx.close(), 1500)
  } catch (e) {
    console.warn('No se pudo reproducir la alarma', e)
  }
}

async function acceptIncident (incidentId) {
  try {
    await api.post(`/emergencies/${incidentId}/accept`)
    $q.notify({ type: 'positive', message: '¡Caso tomado con éxito! Asignado a su guardia.' })
    await loadActiveIncidents()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'No se pudo tomar el caso: ' + (err.response?.data?.detail || err.message) })
  }
}

function openResolveDialog (incident) {
  resolveDialog.incidentId = incident.id
  resolveDialog.triageNotes = ''
  resolveDialog.show = true
}

async function submitResolve () {
  try {
    await api.post(`/emergencies/${resolveDialog.incidentId}/resolve`, {
      triage_notes: resolveDialog.triageNotes.trim()
    })
    $q.notify({ type: 'positive', message: 'Caso cerrado y resuelto exitosamente.' })
    resolveDialog.show = false
    await loadActiveIncidents()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error al resolver: ' + (err.response?.data?.detail || err.message) })
  }
}

async function openAuditDialog (incidentId) {
  try {
    const { data } = await api.get(`/emergencies/${incidentId}/audit-timeline`)
    auditDialog.logs = data
    auditDialog.show = true
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error al consultar auditoría: ' + (err.response?.data?.detail || err.message) })
  }
}

function initWebSocket () {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  let wsHost = `${window.location.hostname}:8000`
  if (process.env.API_URL) {
    try {
      const parsed = new URL(process.env.API_URL)
      wsHost = parsed.host
    } catch {
      wsHost = process.env.API_URL.replace(/^https?:\/\//, '').replace(/\/.*$/, '')
    }
  }
  const token = getAuthToken()
  if (!token) return
  const wsUrl = `${protocol}//${wsHost}/api/v1/emergencies/ws/control-tower?token=${encodeURIComponent(token)}`

  try {
    ws = new WebSocket(wsUrl)
    ws.onopen = () => {
      wsConnected.value = true
    }
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (['INCIDENT_CREATED', 'INCIDENT_ESCALATED'].includes(msg.event)) {
          playAlarm()
        }
        $q.notify({
          type: 'info',
          icon: 'radar',
          message: `Evento de Urgencia: ${msg.event}`,
          position: 'top-right'
        })
        loadActiveIncidents()
      } catch (e) {
        console.error('Error procesando evento WS', e)
      }
    }
    ws.onclose = () => {
      wsConnected.value = false
      if (!unmounted) setTimeout(initWebSocket, 5000)
    }
    ws.onerror = () => {
      wsConnected.value = false
    }
  } catch (e) {
    console.error('Error conectando a WS', e)
  }
}

onMounted(() => {
  loadActiveIncidents()
  if (canUseLiveChannel.value) {
    initWebSocket()
  } else {
    // Admin de sede: sondeo cada 10 s del endpoint filtrado por su clínica.
    pollTimer = setInterval(loadActiveIncidents, 10000)
  }
})

onUnmounted(() => {
  unmounted = true
  if (pollTimer) clearInterval(pollTimer)
  if (ws) {
    ws.close()
  }
})
</script>
