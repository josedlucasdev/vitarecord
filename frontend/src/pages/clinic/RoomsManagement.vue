<template>
  <q-page class="p-6 max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div>
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold">
            <q-icon name="meeting_room" size="22px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">Gestión de Consultorios Físicos</h1>
            <p class="text-xs text-slate-500">
              Administración de salas físicas, especialidades y exclusión mutua de agenda (<code class="text-2xs bg-slate-100 px-1 py-0.5 rounded">room_schedule_locks</code>)
            </p>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <!-- Selector de Sede para SuperAdmin -->
        <q-select
          v-if="user?.role === 'SUPERADMIN' && clinicOptions.length > 0"
          v-model="activeClinicId"
          :options="clinicOptions"
          option-value="id"
          option-label="name"
          emit-value
          map-options
          dense
          outlined
          rounded
          class="min-w-[240px] text-xs bg-slate-50"
          label="Sede / Clínica"
          @update:model-value="fetchRooms"
        />

        <q-btn
          outline
          color="primary"
          icon="refresh"
          label="Actualizar"
          no-caps
          :loading="loading"
          @click="fetchRooms"
        />
        <q-btn
          v-if="can('rooms:manage')"
          color="primary"
          icon="add"
          label="Nuevo Consultorio"
          no-caps
          class="font-semibold"
          @click="openCreateDialog"
        />
      </div>
    </div>

    <!-- Alert Banner -->
    <div class="p-4 bg-teal-50 border border-teal-200 rounded-xl flex items-start gap-3">
      <q-icon name="info" color="teal" size="20px" class="mt-0.5" />
      <div class="text-xs text-teal-900">
        <span class="font-bold">Garantía de Mutex Físico y Capacidad por Especialidad:</span> Cada consultorio físico registrado asegura una cerradura mutex en la base de datos (<code class="bg-teal-100 px-1 py-0.5 rounded font-mono">room_schedule_locks</code>). La disponibilidad de citas depende tanto de la agenda del médico como de la disponibilidad de un consultorio compatible y operativo. Los consultorios en <span class="font-semibold text-amber-700">Mantenimiento</span> o <span class="font-semibold text-rose-700">Inactivos</span> no admitirán agendamientos.
      </div>
    </div>

    <!-- Filtros de Estado -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div class="flex items-center gap-2">
        <q-btn
          v-for="filter in statusFilters"
          :key="filter.value"
          dense
          no-caps
          rounded
          unelevated
          class="px-3 text-xs"
          :class="currentFilter === filter.value ? 'bg-teal-700 text-white font-bold' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'"
          @click="currentFilter = filter.value"
        >
          {{ filter.label }}
          <q-badge rounded color="slate" class="ml-1 text-2xs" :label="filterCount(filter.value)" />
        </q-btn>
      </div>

      <div class="text-xs text-slate-500">
        Mostrando <span class="font-bold text-slate-800">{{ filteredRooms.length }}</span> de {{ rooms.length }} consultorios
      </div>
    </div>

    <!-- State: Loading -->
    <div v-if="loading" class="flex justify-center p-12">
      <q-spinner-dots color="primary" size="48px" />
    </div>

    <!-- State: Empty -->
    <div
      v-else-if="filteredRooms.length === 0"
      class="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4 shadow-sm"
    >
      <div class="w-16 h-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
        <q-icon name="door_front" size="32px" />
      </div>
      <h3 class="text-lg font-bold text-slate-800">No hay consultorios en este criterio</h3>
      <p class="text-xs text-slate-500 max-w-md mx-auto">
        No se encontraron salas registradas con el filtro seleccionado.
      </p>
      <q-btn
        v-if="can('rooms:manage') && rooms.length === 0"
        color="primary"
        icon="add"
        label="Registrar Primer Consultorio"
        no-caps
        @click="openCreateDialog"
      />
    </div>

    <!-- Rooms Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="room in filteredRooms"
        :key="room.id"
        class="bg-white rounded-2xl border p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
        :class="getCardBorderClass(room)"
      >
        <div>
          <!-- Header de Tarjeta -->
          <div class="flex items-center justify-between">
            <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200">
              Nº {{ room.room_number || 'S/N' }}
            </span>
            <span
              :class="getStatusBadgeClass(room)"
              class="px-2.5 py-1 rounded-full text-2xs font-bold uppercase tracking-wider border"
            >
              {{ getStatusLabel(room) }}
            </span>
          </div>

          <!-- Nombre y Especialidad -->
          <h3 class="mt-3 font-bold text-slate-900 text-base leading-snug">{{ room.name }}</h3>

          <div class="mt-2 flex flex-wrap items-center gap-1.5">
            <span
              v-if="room.specialty"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-cyan-50 text-cyan-800 border border-cyan-200"
            >
              <q-icon name="medical_services" size="13px" />
              {{ room.specialty }}
            </span>
            <span
              v-else
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200"
            >
              <q-icon name="view_cozy" size="13px" />
              Polivalente (Cualquier Especialidad)
            </span>
          </div>

          <!-- Horario de Operación -->
          <div class="mt-2 text-xs text-slate-600 flex items-center gap-1">
            <q-icon name="schedule" size="14px" color="teal" />
            <span>Horario: <strong>{{ formatOperatingHours(room.operating_hours) }}</strong></span>
          </div>

          <!-- Descripción / Equipamiento -->
          <p class="mt-2 text-xs text-slate-500 line-clamp-2">
            {{ room.description || 'Sin equipamiento ni notas registradas.' }}
          </p>

          <!-- Mutex Lock Badge -->
          <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-2xs text-slate-400">
            <span class="flex items-center">
              <q-icon name="lock" size="14px" class="mr-1 text-teal-600" />
              Mutex Lock Activo
            </span>
            <span>ID: {{ room.id.substring(0, 8) }}...</span>
          </div>
        </div>

        <!-- Acciones Administrativas -->
        <div v-if="can('rooms:manage')" class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
          <!-- Botón de Mantenimiento Rápido -->
          <q-btn
            v-if="room.status === 'ACTIVE'"
            flat
            dense
            color="amber-9"
            icon="build"
            label="Mantenimiento"
            no-caps
            class="text-xs"
            @click="toggleMaintenance(room)"
          >
            <q-tooltip>Poner en mantenimiento temporal (bloquea nuevas reservas)</q-tooltip>
          </q-btn>
          <q-btn
            v-else-if="room.status === 'MAINTENANCE'"
            flat
            dense
            color="positive"
            icon="check_circle"
            label="Habilitar"
            no-caps
            class="text-xs font-bold"
            @click="toggleMaintenance(room)"
          >
            <q-tooltip>Reactivar consultorio (admite reservas)</q-tooltip>
          </q-btn>
          <div v-else />

          <div class="flex items-center gap-1">
            <q-btn
              flat
              dense
              color="primary"
              icon="edit"
              label="Editar"
              no-caps
              class="text-xs"
              @click="openEditDialog(room)"
            />
            <q-btn
              v-if="room.status !== 'INACTIVE'"
              flat
              dense
              color="negative"
              icon="delete"
              label="Desactivar"
              no-caps
              class="text-xs"
              @click="confirmDeactivate(room)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Create / Edit Dialog -->
    <q-dialog v-model="showDialog">
      <q-card style="min-width: 480px; max-width: 560px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-teal-700 to-cyan-800 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon :name="isEditing ? 'edit' : 'add_business'" size="24px" />
            <h3 class="text-lg font-bold">{{ isEditing ? 'Editar Consultorio' : 'Registrar Nuevo Consultorio' }}</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6 space-y-4">
          <form class="space-y-4" @submit.prevent="saveRoom">
            <q-input
              v-model="form.name"
              label="Nombre del Consultorio *"
              placeholder="Ej. Consultorio 101 - Ginecología General"
              filled
              required
            />
            <q-input
              v-model="form.room_number"
              label="Número / Identificador de Puerta *"
              placeholder="Ej. 101"
              filled
              required
            />

            <!-- Especialidad del Consultorio -->
            <q-select
              v-model="form.specialty"
              :options="specialtyOptions"
              label="Especialidad Asignada (Opcional)"
              filled
              clearable
              use-input
              new-value-mode="add-unique"
              hint="Si lo deja vacío o selecciona 'Polivalente', admitirá cualquier especialidad médica"
            >
              <template #prepend>
                <q-icon name="medical_services" color="teal" />
              </template>
            </q-select>

            <!-- Estado Operativo -->
            <q-select
              v-model="form.status"
              :options="statusOptions"
              emit-value
              map-options
              label="Estado Operativo *"
              filled
              required
            >
              <template #prepend>
                <q-icon
                  :name="form.status === 'ACTIVE' ? 'check_circle' : (form.status === 'MAINTENANCE' ? 'build' : 'block')"
                  :color="form.status === 'ACTIVE' ? 'positive' : (form.status === 'MAINTENANCE' ? 'amber-9' : 'negative')"
                />
              </template>
            </q-select>

            <!-- Horario de Operación -->
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-2">
              <label class="text-xs font-semibold text-slate-700 flex items-center gap-1">
                <q-icon name="schedule" color="teal" /> Horario Diario de Operación
              </label>
              <div class="grid grid-cols-2 gap-3">
                <q-input
                  v-model="form.start_time"
                  label="Hora de Apertura"
                  type="time"
                  filled
                  dense
                />
                <q-input
                  v-model="form.end_time"
                  label="Hora de Cierre"
                  type="time"
                  filled
                  dense
                />
              </div>
            </div>

            <q-input
              v-model="form.description"
              label="Equipamiento y Detalles (Opcional)"
              placeholder="Ej. Camilla ginecológica, ecógrafo 3D, lavamanos quirúrgico"
              type="textarea"
              rows="3"
              filled
            />

            <div v-if="formError" class="p-3 bg-red-50 text-red-700 text-xs rounded-lg flex items-center">
              <q-icon name="warning" class="mr-2" size="16px" />
              <span>{{ formError }}</span>
            </div>

            <div class="pt-2 flex justify-end space-x-3">
              <q-btn flat label="Cancelar" v-close-popup no-caps />
              <q-btn
                type="submit"
                color="primary"
                :label="isEditing ? 'Guardar Cambios' : 'Crear Consultorio'"
                no-caps
                class="font-semibold"
                :loading="submitting"
              />
            </div>
          </form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Dialog, Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'

const { can, user } = useAcl()

const DEFAULT_CLINIC_ID = 'c1111111-1111-1111-1111-111111111111'
const activeClinicId = ref(user.value?.clinicId || DEFAULT_CLINIC_ID)
const clinicOptions = ref([])

const rooms = ref([])
const loading = ref(false)
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formError = ref('')
const currentFilter = ref('ALL')

const statusFilters = [
  { label: 'Todos', value: 'ALL' },
  { label: 'Operativos', value: 'ACTIVE' },
  { label: 'En Mantenimiento', value: 'MAINTENANCE' },
  { label: 'Inactivos', value: 'INACTIVE' }
]

const specialtyOptions = [
  'Ginecología & Obstetricia',
  'Medicina Materno-Fetal',
  'Fertilidad & Reproducción Asistida',
  'Ginecología Oncológica',
  'Mastología & Patología Mamaria',
  'Endocrinología Ginecológica',
  'Urología Ginecológica & Piso Pélvico',
  'Perinatología & Alto Riesgo',
  'Pediatría',
  'Medicina Interna',
  'Medicina General'
]

const statusOptions = [
  { label: 'Operativo (Disponible para citas)', value: 'ACTIVE' },
  { label: 'En Mantenimiento / Reparación (No disponible)', value: 'MAINTENANCE' },
  { label: 'Inactivo / Fuera de servicio', value: 'INACTIVE' }
]

const form = reactive({
  name: '',
  room_number: '',
  specialty: null,
  status: 'ACTIVE',
  start_time: '07:00',
  end_time: '19:00',
  description: ''
})

const filteredRooms = computed(() => {
  if (currentFilter.value === 'ALL') return rooms.value
  return rooms.value.filter(r => (r.status || (r.is_active ? 'ACTIVE' : 'INACTIVE')) === currentFilter.value)
})

function filterCount (filterVal) {
  if (filterVal === 'ALL') return rooms.value.length
  return rooms.value.filter(r => (r.status || (r.is_active ? 'ACTIVE' : 'INACTIVE')) === filterVal).length
}

function getStatusBadgeClass (room) {
  const st = room.status || (room.is_active ? 'ACTIVE' : 'INACTIVE')
  if (st === 'ACTIVE') return 'bg-emerald-50 text-emerald-800 border-emerald-200'
  if (st === 'MAINTENANCE') return 'bg-amber-50 text-amber-900 border-amber-300'
  return 'bg-rose-50 text-rose-800 border-rose-200'
}

function getStatusLabel (room) {
  const st = room.status || (room.is_active ? 'ACTIVE' : 'INACTIVE')
  if (st === 'ACTIVE') return 'Operativo'
  if (st === 'MAINTENANCE') return 'En Mantenimiento'
  return 'Inactivo'
}

function getCardBorderClass (room) {
  const st = room.status || (room.is_active ? 'ACTIVE' : 'INACTIVE')
  if (st === 'MAINTENANCE') return 'border-amber-300 bg-amber-50/10'
  if (st === 'INACTIVE') return 'border-slate-200 opacity-60'
  return 'border-slate-200'
}

function formatOperatingHours (op) {
  if (!op) return '07:00 - 19:00'
  if (op.start && op.end) return `${op.start} - ${op.end}`
  return 'Jornada Continua'
}

async function fetchClinics () {
  if (user.value?.role !== 'SUPERADMIN') return
  try {
    const { data } = await api.get('/clinics/public')
    clinicOptions.value = data
    if (!clinicOptions.value.find(c => c.id === activeClinicId.value) && clinicOptions.value.length > 0) {
      activeClinicId.value = clinicOptions.value[0].id
    }
  } catch (err) {
    console.error('Error al cargar sedes:', err)
  }
}

async function fetchRooms () {
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.get(`/clinics/${activeClinicId.value}/rooms`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    rooms.value = data
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al cargar los consultorios.'
    })
  } finally {
    loading.value = false
  }
}

function openCreateDialog () {
  isEditing.value = false
  editingId.value = null
  form.name = ''
  form.room_number = ''
  form.specialty = null
  form.status = 'ACTIVE'
  form.start_time = '07:00'
  form.end_time = '19:00'
  form.description = ''
  formError.value = ''
  showDialog.value = true
}

function openEditDialog (room) {
  isEditing.value = true
  editingId.value = room.id
  form.name = room.name
  form.room_number = room.room_number || ''
  form.specialty = room.specialty || null
  form.status = room.status || (room.is_active ? 'ACTIVE' : 'INACTIVE')
  const op = room.operating_hours || {}
  form.start_time = op.start || '07:00'
  form.end_time = op.end || '19:00'
  form.description = room.description || ''
  formError.value = ''
  showDialog.value = true
}

async function saveRoom () {
  submitting.value = true
  formError.value = ''
  try {
    const token = localStorage.getItem('access_token')
    const payload = {
      name: form.name,
      room_number: form.room_number,
      specialty: form.specialty || null,
      status: form.status,
      operating_hours: {
        start: form.start_time || '07:00',
        end: form.end_time || '19:00'
      },
      description: form.description,
      is_active: form.status !== 'INACTIVE'
    }

    if (isEditing.value) {
      await api.put(`/clinics/${activeClinicId.value}/rooms/${editingId.value}`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      })
      Notify.create({ type: 'positive', message: 'Consultorio actualizado exitosamente.' })
    } else {
      await api.post(`/clinics/${activeClinicId.value}/rooms`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      })
      Notify.create({ type: 'positive', message: 'Consultorio y cerrojo Mutex creados exitosamente.' })
    }
    showDialog.value = false
    await fetchRooms()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Error al guardar consultorio.'
  } finally {
    submitting.value = false
  }
}

async function toggleMaintenance (room) {
  const isNowMaint = room.status === 'MAINTENANCE'
  const newStatus = isNowMaint ? 'ACTIVE' : 'MAINTENANCE'
  const actionText = isNowMaint ? 'Reactivar Consultorio' : 'Poner en Mantenimiento'
  const messageText = isNowMaint
    ? `¿Deseas reactivar "${room.name}"? Volverá a estar disponible para citas de especialistas compatibles.`
    : `¿Confirmas poner en mantenimiento "${room.name}"? Ningún paciente podrá agendar citas en este consultorio mientras esté en reparación o mantenimiento.`

  Dialog.create({
    title: actionText,
    message: messageText,
    cancel: true,
    persistent: true,
    ok: { label: isNowMaint ? 'Reactivar' : 'Poner en Mantenimiento', color: isNowMaint ? 'positive' : 'amber-9' }
  }).onOk(async () => {
    try {
      const token = localStorage.getItem('access_token')
      await api.put(`/clinics/${activeClinicId.value}/rooms/${room.id}`, {
        status: newStatus
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      Notify.create({
        type: isNowMaint ? 'positive' : 'warning',
        message: isNowMaint ? 'Consultorio reactivado correctamente.' : 'Consultorio marcado en mantenimiento.'
      })
      await fetchRooms()
    } catch (err) {
      Notify.create({
        type: 'negative',
        message: err.response?.data?.detail || 'Error al cambiar estado del consultorio.'
      })
    }
  })
}

function confirmDeactivate (room) {
  Dialog.create({
    title: 'Desactivar Consultorio',
    message: `¿Estás seguro de desactivar "${room.name}"? Los turnos ya asignados conservarán su historial, pero no se permitirán nuevos agendamientos.`,
    cancel: true,
    persistent: true,
    ok: { label: 'Desactivar', color: 'negative' }
  }).onOk(async () => {
    try {
      const token = localStorage.getItem('access_token')
      await api.delete(`/clinics/${activeClinicId.value}/rooms/${room.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      Notify.create({ type: 'info', message: 'Consultorio desactivado.' })
      await fetchRooms()
    } catch (err) {
      Notify.create({
        type: 'negative',
        message: err.response?.data?.detail || 'No se pudo desactivar el consultorio.'
      })
    }
  })
}

onMounted(async () => {
  await fetchClinics()
  await fetchRooms()
})
</script>
