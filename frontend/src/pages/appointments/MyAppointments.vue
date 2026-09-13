<template>
  <q-page class="p-6 max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div>
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold">
            <q-icon name="calendar_today" size="22px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">Gestión de Citas Médicas</h1>
            <p class="text-xs text-slate-500">
              Seguimiento de turnos, estado de aceptación del paciente y estatus de pago en caja.
            </p>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <q-btn
          flat
          color="teal-8"
          icon="notifications_active"
          label="Mis Canales"
          no-caps
          class="font-semibold bg-teal-50/70 border border-teal-200/60"
          @click="showNotificationModal = true"
        >
          <q-tooltip>Configurar canales de notificación (WhatsApp, SMS, Email)</q-tooltip>
        </q-btn>
        <q-btn
          outline
          color="primary"
          icon="refresh"
          label="Actualizar"
          no-caps
          :loading="loading"
          @click="fetchAppointments"
        />
        <q-btn
          color="primary"
          icon="add"
          label="Agendar Cita"
          to="/appointments/book"
          no-caps
          class="font-semibold shadow-sm"
        />
      </div>

    </div>

    <!-- Banner informativo específico para Pacientes -->
    <div
      v-if="currentUserRole === 'PATIENT'"
      class="bg-gradient-to-r from-teal-50 via-cyan-50 to-blue-50 border border-teal-200/80 rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4"
    >
      <div class="flex items-start space-x-3.5">
        <div class="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold shrink-0 mt-0.5 shadow-sm">
          <q-icon name="favorite" size="20px" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-teal-950">Portal del Paciente • VitaRecord</h2>
          <p class="text-xs text-slate-600 mt-0.5 leading-relaxed">
            Aquí puedes consultar el estado de tus citas médicas, ingresar a tus consultas y acceder a tus recetas electrónicas oficiales con código QR.
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <q-btn
          to="/medical/history"
          color="teal-8"
          outline
          icon="folder_shared"
          label="Mi Historial Clínico"
          no-caps
          class="text-xs font-semibold"
        />
        <q-btn
          to="/appointments/book"
          color="teal-8"
          icon="event_available"
          label="Nueva Cita"
          no-caps
          class="text-xs font-bold"
        />
      </div>
    </div>

    <!-- State: Loading -->
    <div v-if="loading" class="flex justify-center p-12">
      <q-spinner-dots color="primary" size="48px" />
    </div>

    <!-- State: Empty -->
    <div
      v-else-if="appointments.length === 0"
      class="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4 shadow-sm"
    >
      <div class="w-16 h-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
        <q-icon name="event_busy" size="32px" />
      </div>
      <h3 class="text-lg font-bold text-slate-800">No hay citas registradas</h3>
      <p class="text-xs text-slate-500 max-w-md mx-auto">
        Comienza agendando tu primera cita médica con los especialistas disponibles en la clínica.
      </p>
      <q-btn
        color="primary"
        icon="event_available"
        label="Agendar Mi Primera Cita"
        to="/appointments/book"
        no-caps
      />
    </div>

    <!-- Appointments List -->
    <div v-else class="space-y-4">
      <div
        v-for="app in appointments"
        :key="app.id"
        class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <!-- Info Principal -->
        <div class="space-y-2">
          <div class="flex flex-wrap items-center gap-2">
            <!-- Status Badge -->
            <span
              :class="statusBadgeClass(app.status)"
              class="px-2.5 py-1 rounded-full text-2xs font-bold uppercase tracking-wider"
            >
              {{ formatStatus(app.status) }}
            </span>

            <!-- Payment Badge -->
            <span
              :class="paymentBadgeClass(app.payment_status)"
              class="px-2.5 py-1 rounded-full text-2xs font-semibold"
            >
              Pago: {{ app.payment_status }} • ${{ app.payment_amount }} {{ app.currency || 'USD' }}
            </span>

            <!-- Clinic Badge -->
            <span v-if="app.clinic_name" class="px-2.5 py-1 rounded-full text-2xs font-semibold bg-slate-100 text-slate-700 flex items-center">
              <q-icon name="apartment" size="14px" class="mr-1 text-teal-600" />
              {{ app.clinic_name }}
            </span>

            <span v-if="app.room_name" class="text-2xs font-medium text-slate-500 flex items-center">
              <q-icon name="meeting_room" size="14px" class="mr-1 text-teal-600" />
              {{ app.room_name }}
            </span>
          </div>

          <div>
            <h3 class="font-bold text-slate-900 text-base">
              {{ app.doctor_name || 'Médico Especialista' }}
            </h3>
            <p class="text-xs text-slate-500">
              Paciente: <span class="font-semibold text-slate-700">{{ app.patient_name || 'Titular' }}</span>
              <span v-if="app.dependent_id" class="text-teal-700 font-semibold ml-1">(Familiar)</span>
            </p>
            <p v-if="app.reason" class="text-xs text-slate-600 mt-1 italic">
              "{{ app.reason }}"
            </p>
          </div>

          <div class="text-xs text-slate-500 flex items-center gap-4">
            <span class="flex items-center">
              <q-icon name="today" size="16px" class="mr-1 text-slate-400" />
              {{ formatDate(app.start_time) }}
            </span>
            <span class="flex items-center font-semibold text-slate-700">
              <q-icon name="schedule" size="16px" class="mr-1 text-teal-600" />
              {{ formatTime(app.start_time) }} - {{ formatTime(app.end_time) }}
            </span>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex flex-wrap items-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100">
          <!-- Botón Ficha de Triage y Medidas -->
          <q-btn
            v-if="app.intake_data && Object.keys(app.intake_data).length > 0"
            flat
            color="teal-8"
            icon="monitor_heart"
            label="Ficha de Triage"
            no-caps
            dense
            class="px-2.5 py-1 text-xs font-semibold bg-teal-50/80 rounded-xl"
            @click="openTriageModal(app)"
          />

          <!-- Si está en PENDING_DOCTOR_APPROVAL -> Acciones para el médico -->
          <template v-if="app.status === 'PENDING_DOCTOR_APPROVAL'">
            <q-btn
              v-if="currentUserRole === 'DOCTOR'"
              color="teal-8"
              icon="check"
              label="Aceptar y Enviar Invitación"
              no-caps
              dense
              class="px-3 py-1.5 text-xs font-bold shadow-sm"
              :loading="processingAcceptId === app.id"
              @click="doctorAcceptApp(app.id)"
            >
              <q-tooltip>Confirmar cita y enviar correo de activación institucional al paciente</q-tooltip>
            </q-btn>
            <q-btn
              v-if="currentUserRole === 'DOCTOR'"
              color="negative"
              outline
              icon="close"
              label="Rechazar"
              no-caps
              dense
              class="px-3 py-1.5 text-xs font-semibold"
              @click="promptDoctorReject(app.id)"
            />
            <span v-else class="text-2xs text-amber-800 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full font-semibold">
              En revisión por el médico especialista
            </span>
          </template>

          <!-- Si el médico puede iniciar la consulta médica -->
          <q-btn
            v-if="currentUserRole === 'DOCTOR' && ['CONFIRMED', 'SCHEDULED', 'CHECKED_IN', 'IN_CONSULTATION'].includes(app.status)"
            color="teal"
            icon="medical_services"
            label="Atender Paciente"
            no-caps
            dense
            class="px-3 py-1.5 text-xs font-bold shadow-xs"
            :to="`/medical/consultation?appointment_id=${app.id}`"
          />

          <!-- Si la cita ya está completada con historia y receta -->
          <q-btn
            v-if="app.status === 'COMPLETED'"
            outline
            color="teal"
            icon="description"
            label="Ver Historia / Receta"
            no-caps
            dense
            class="px-3 py-1.5 text-xs font-semibold"
            :to="currentUserRole === 'PATIENT' ? '/medical/history' : `/medical/consultation?appointment_id=${app.id}`"
          />

          <!-- Si está en PENDING_PATIENT_ACCEPTANCE -> Botones Aceptar / Rechazar -->
          <template v-if="app.status === 'PENDING_PATIENT_ACCEPTANCE'">
            <q-btn
              color="positive"
              icon="check"
              label="Aceptar Cita"
              no-caps
              dense
              class="px-3 py-1.5 text-xs font-bold shadow-sm"
              @click="acceptApp(app.id)"
            />
            <q-btn
              color="negative"
              outline
              icon="close"
              label="Rechazar"
              no-caps
              dense
              class="px-3 py-1.5 text-xs font-semibold"
              @click="rejectApp(app.id)"
            />
          </template>

          <!-- Si está CONFIRMED o SCHEDULED -> Botón Cancelar -->
          <template v-else-if="['CONFIRMED', 'SCHEDULED'].includes(app.status)">
            <q-btn
              flat
              color="negative"
              icon="cancel"
              label="Cancelar Cita"
              no-caps
              dense
              class="text-xs"
              @click="promptCancel(app.id)"
            />
          </template>
        </div>
      </div>
    </div>

    <!-- Modal Ficha de Triage y Medidas Biométricas -->
    <q-dialog v-model="showTriageModal">
      <q-card v-if="selectedTriageApp" style="min-width: 440px; max-width: 580px; border-radius: 24px;" class="overflow-hidden">
        <q-card-section class="bg-gradient-to-r from-teal-700 via-cyan-700 to-blue-800 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="monitor_heart" size="24px" />
            <div>
              <h3 class="text-base font-bold leading-none">Ficha de Triage y Medidas</h3>
              <p class="text-2xs text-teal-100 mt-1">Datos biométricos y antecedentes del paciente</p>
            </div>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6 space-y-4 text-xs">
          <!-- Paciente info -->
          <div class="bg-slate-50 p-3.5 rounded-2xl border border-slate-200 grid grid-cols-2 gap-2 text-slate-700">
            <div>
              <span class="text-slate-400 block text-2xs uppercase font-bold">Paciente:</span>
              <span class="font-bold text-sm text-slate-900">{{ selectedTriageApp.patient_name || 'Paciente' }}</span>
            </div>
            <div>
              <span class="text-slate-400 block text-2xs uppercase font-bold">Documento / Cédula:</span>
              <span class="font-semibold">{{ selectedTriageApp.intake_data?.id_document || 'No registrado' }}</span>
            </div>
            <div v-if="selectedTriageApp.patient_email">
              <span class="text-slate-400 block text-2xs uppercase font-bold">Correo:</span>
              <span>{{ selectedTriageApp.patient_email }}</span>
            </div>
            <div v-if="selectedTriageApp.patient_phone">
              <span class="text-slate-400 block text-2xs uppercase font-bold">Teléfono:</span>
              <span>{{ selectedTriageApp.patient_phone }}</span>
            </div>
            <div v-if="selectedTriageApp.intake_data?.address" class="col-span-2 pt-1 border-t border-slate-200">
              <span class="text-slate-400 block text-2xs uppercase font-bold">Dirección:</span>
              <span>{{ selectedTriageApp.intake_data.address }}, {{ selectedTriageApp.intake_data.city || '' }} ({{ selectedTriageApp.intake_data.country || 'VE' }})</span>
            </div>
          </div>

          <!-- Métricas Biométricas -->
          <div class="grid grid-cols-3 gap-3 text-center">
            <div class="p-3 bg-teal-50 rounded-2xl border border-teal-100">
              <div class="text-2xs text-teal-700 font-bold uppercase">Estatura</div>
              <div class="text-base font-black text-teal-900 mt-0.5">
                {{ selectedTriageApp.intake_data?.height_cm ? `${selectedTriageApp.intake_data.height_cm} cm` : 'N/D' }}
              </div>
            </div>
            <div class="p-3 bg-teal-50 rounded-2xl border border-teal-100">
              <div class="text-2xs text-teal-700 font-bold uppercase">Peso</div>
              <div class="text-base font-black text-teal-900 mt-0.5">
                {{ selectedTriageApp.intake_data?.weight_kg ? `${selectedTriageApp.intake_data.weight_kg} kg` : 'N/D' }}
              </div>
            </div>
            <div class="p-3 bg-teal-50 rounded-2xl border border-teal-100">
              <div class="text-2xs text-teal-700 font-bold uppercase">IMC</div>
              <div class="text-base font-black text-teal-900 mt-0.5">
                {{ selectedTriageApp.intake_data?.bmi || 'N/D' }}
              </div>
              <div v-if="selectedTriageApp.intake_data?.bmi_category" class="text-2xs font-semibold text-teal-700">
                {{ selectedTriageApp.intake_data.bmi_category }}
              </div>
            </div>
          </div>

          <!-- Antecedentes y Detalles Clínicos -->
          <div class="space-y-2.5">
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span class="text-slate-400 block text-2xs font-bold uppercase">Grupo Sanguíneo:</span>
              <span class="font-bold text-slate-800">{{ selectedTriageApp.intake_data?.blood_type || 'No especificado' }}</span>
            </div>

            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span class="text-slate-400 block text-2xs font-bold uppercase">Alergias Conocidas:</span>
              <span class="font-medium text-slate-800" :class="{ 'text-red-700 font-bold': selectedTriageApp.intake_data?.allergies && !selectedTriageApp.intake_data.allergies.toLowerCase().includes('ningun') }">
                {{ selectedTriageApp.intake_data?.allergies || 'Ninguna reportada' }}
              </span>
            </div>

            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span class="text-slate-400 block text-2xs font-bold uppercase">Antecedentes / Enfermedades Crónicas:</span>
              <span class="font-medium text-slate-800">{{ selectedTriageApp.intake_data?.chronic_conditions || 'Sin antecedentes' }}</span>
            </div>

            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span class="text-slate-400 block text-2xs font-bold uppercase">Medicación Actual:</span>
              <span class="font-medium text-slate-800">{{ selectedTriageApp.intake_data?.current_medications || 'No reportada' }}</span>
            </div>

            <div class="bg-amber-50/80 p-3 rounded-xl border border-amber-200 text-amber-950">
              <span class="text-amber-800 block text-2xs font-bold uppercase">Motivo de Consulta / Síntomas:</span>
              <span class="font-medium italic">"{{ selectedTriageApp.reason || selectedTriageApp.intake_data?.symptoms || 'Control general' }}"</span>
            </div>
          </div>

          <!-- Si el médico está visualizando y la cita está pendiente, botón para aceptar desde el modal -->
          <div v-if="currentUserRole === 'DOCTOR' && selectedTriageApp.status === 'PENDING_DOCTOR_APPROVAL'" class="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <q-btn flat label="Cerrar" v-close-popup no-caps />
            <q-btn
              color="teal-8"
              icon="check"
              label="Aceptar Cita y Enviar Invitación"
              no-caps
              class="font-bold"
              @click="doctorAcceptApp(selectedTriageApp.id); showTriageModal = false"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Modal de Configuración de Canales de Notificación (Módulo 6) -->
    <NotificationPreferencesModal v-model="showNotificationModal" />
  </q-page>

</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Dialog, Notify } from 'quasar'
import { api } from 'boot/axios'
import NotificationPreferencesModal from 'components/NotificationPreferencesModal.vue'

const appointments = ref([])
const loading = ref(false)
const currentUserRole = ref('')
const showTriageModal = ref(false)
const showNotificationModal = ref(false)
const selectedTriageApp = ref(null)
const processingAcceptId = ref(null)


function openTriageModal (app) {
  selectedTriageApp.value = app
  showTriageModal.value = true
}

async function fetchAppointments () {
  loading.value = true
  try {
    const { data } = await api.get('/appointments')
    appointments.value = data
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al cargar citas médicas.' })
  } finally {
    loading.value = false
  }
}

async function doctorAcceptApp (appId) {
  processingAcceptId.value = appId
  try {
    await api.post(`/appointments/${appId}/doctor-accept`)
    Notify.create({
      type: 'positive',
      message: '¡Cita aceptada con éxito! Se ha enviado la invitación institucional y enlace de activación al correo del paciente.',
      icon: 'mark_email_read'
    })
    await fetchAppointments()
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudo aceptar la cita médica.'
    })
  } finally {
    processingAcceptId.value = null
  }
}

function promptDoctorReject (appId) {
  Dialog.create({
    title: 'Rechazar Cita Solicitada',
    message: 'Indica el motivo por el cual no puedes atender esta solicitud de cita:',
    prompt: {
      model: '',
      type: 'text',
      placeholder: 'Ej. Horario no disponible, requiere otra especialidad...'
    },
    cancel: true,
    persistent: true,
    ok: { label: 'Rechazar Cita', color: 'negative' }
  }).onOk(async (reason) => {
    try {
      await api.post(`/appointments/${appId}/doctor-reject`, {
        cancellation_reason: reason || 'Rechazada por el médico'
      })
      Notify.create({ type: 'info', message: 'Solicitud de cita rechazada y horario liberado.' })
      await fetchAppointments()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Error al rechazar cita.' })
    }
  })
}

async function acceptApp (appId) {
  try {
    await api.post(`/appointments/${appId}/accept`)
    Notify.create({ type: 'positive', message: '¡Cita confirmada formalmente!' })
    await fetchAppointments()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.response?.data?.detail || 'No se pudo aceptar la cita.' })
  }
}

function rejectApp (appId) {
  Dialog.create({
    title: 'Rechazar Cita Propuesta',
    message: '¿Deseas rechazar esta cita? El horario y el consultorio se liberarán de inmediato en la clínica.',
    cancel: true,
    persistent: true,
    ok: { label: 'Rechazar', color: 'negative' }
  }).onOk(async () => {
    try {
      await api.post(`/appointments/${appId}/reject`)
      Notify.create({ type: 'info', message: 'Cita rechazada. Horario liberado y cobro exento.' })
      await fetchAppointments()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Error al rechazar cita.' })
    }
  })
}

function promptCancel (appId) {
  Dialog.create({
    title: 'Cancelar Cita',
    message: 'Indica el motivo de la cancelación. El turno quedará disponible de inmediato para otros pacientes:',
    prompt: {
      model: '',
      type: 'text',
      placeholder: 'Ej. Incompatibilidad de horario'
    },
    cancel: true,
    persistent: true,
    ok: { label: 'Cancelar Cita', color: 'negative' }
  }).onOk(async (reason) => {
    try {
      await api.post(`/appointments/${appId}/cancel`, {
        cancellation_reason: reason || 'Cancelada por el usuario'
      })
      Notify.create({ type: 'info', message: 'Cita cancelada exitosamente y horario liberado.' })
      await fetchAppointments()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Error al cancelar cita.' })
    }
  })
}

function formatDate (isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleDateString('es-ES', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

function formatTime (isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatStatus (s) {
  const map = {
    PENDING_DOCTOR_APPROVAL: 'Pendiente por Aprobar',
    PENDING_PATIENT_ACCEPTANCE: 'Esperando Aceptación del Paciente',
    SCHEDULED: 'Agendada',
    CONFIRMED: 'Confirmada',
    CHECKED_IN: 'En Sala de Espera',
    IN_CONSULTATION: 'En Consulta',
    COMPLETED: 'Completada',
    CANCELLED_BY_PATIENT: 'Cancelada por Paciente',
    CANCELLED_BY_DOCTOR: 'Cancelada por Médico',
    CANCELLED_BY_CLINIC: 'Cancelada por Clínica',
    REJECTED_BY_PATIENT: 'Rechazada por Paciente',
    REJECTED_BY_DOCTOR: 'Rechazada por Médico'
  }
  return map[s] || s
}

function statusBadgeClass (s) {
  if (s === 'PENDING_DOCTOR_APPROVAL') return 'bg-amber-100 text-amber-900 border border-amber-300 font-bold'
  if (s === 'PENDING_PATIENT_ACCEPTANCE') return 'bg-amber-100 text-amber-900 border border-amber-300 animate-pulse'
  if (s === 'CONFIRMED') return 'bg-emerald-100 text-emerald-800'
  if (s === 'SCHEDULED') return 'bg-blue-100 text-blue-800'
  if (s?.startsWith('CANCELLED') || s === 'REJECTED_BY_PATIENT' || s === 'REJECTED_BY_DOCTOR') return 'bg-rose-100 text-rose-800'
  return 'bg-slate-100 text-slate-800'
}

function paymentBadgeClass (p) {
  if (p === 'PAID') return 'bg-emerald-50 text-emerald-700 border border-emerald-200'
  if (p === 'UNPAID') return 'bg-amber-50 text-amber-700 border border-amber-200'
  if (p === 'EXEMPT') return 'bg-slate-100 text-slate-600'
  if (p === 'VOID') return 'bg-rose-50 text-rose-700 border border-rose-200'
  return 'bg-slate-50 text-slate-600'
}

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/me')
    currentUserRole.value = data.role
  } catch {}
  await fetchAppointments()
})
</script>
