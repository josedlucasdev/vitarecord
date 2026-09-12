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
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Dialog, Notify } from 'quasar'
import { api } from 'boot/axios'

const appointments = ref([])
const loading = ref(false)
const currentUserRole = ref('')

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
    PENDING_PATIENT_ACCEPTANCE: 'Esperando Aceptación del Paciente',
    SCHEDULED: 'Agendada',
    CONFIRMED: 'Confirmada',
    CHECKED_IN: 'En Sala de Espera',
    IN_CONSULTATION: 'En Consulta',
    COMPLETED: 'Completada',
    CANCELLED_BY_PATIENT: 'Cancelada por Paciente',
    CANCELLED_BY_DOCTOR: 'Cancelada por Médico',
    CANCELLED_BY_CLINIC: 'Cancelada por Clínica',
    REJECTED_BY_PATIENT: 'Rechazada por Paciente'
  }
  return map[s] || s
}

function statusBadgeClass (s) {
  if (s === 'PENDING_PATIENT_ACCEPTANCE') return 'bg-amber-100 text-amber-900 border border-amber-300 animate-pulse'
  if (s === 'CONFIRMED') return 'bg-emerald-100 text-emerald-800'
  if (s === 'SCHEDULED') return 'bg-blue-100 text-blue-800'
  if (s?.startsWith('CANCELLED') || s === 'REJECTED_BY_PATIENT') return 'bg-rose-100 text-rose-800'
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
