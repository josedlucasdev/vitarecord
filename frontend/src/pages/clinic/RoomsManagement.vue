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
              Administración de salas físicas con exclusión mutua de agenda (<code class="text-2xs bg-slate-100 px-1 py-0.5 rounded">room_schedule_locks</code>)
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
        <span class="font-bold">Garantía de Mutex Físico:</span> Cada consultorio registrado genera de manera inmediata una fila de cerrojo en la base de datos (<code class="bg-teal-100 px-1 py-0.5 rounded font-mono">room_schedule_locks</code>). Esto evita reservas solapadas mediante bloqueos pesimistas en tiempo real durante el agendamiento.
      </div>
    </div>

    <!-- State: Loading -->
    <div v-if="loading" class="flex justify-center p-12">
      <q-spinner-dots color="primary" size="48px" />
    </div>

    <!-- State: Empty -->
    <div
      v-else-if="rooms.length === 0"
      class="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4 shadow-sm"
    >
      <div class="w-16 h-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
        <q-icon name="door_front" size="32px" />
      </div>
      <h3 class="text-lg font-bold text-slate-800">No hay consultorios registrados</h3>
      <p class="text-xs text-slate-500 max-w-md mx-auto">
        Para comenzar a agendar citas físicas con doctores, registra al menos un consultorio físico en esta sede.
      </p>
      <q-btn
        v-if="can('rooms:manage')"
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
        v-for="room in rooms"
        :key="room.id"
        class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
      >
        <div>
          <div class="flex items-center justify-between">
            <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200">
              Nº {{ room.room_number || 'S/N' }}
            </span>
            <span
              :class="room.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'"
              class="px-2 py-0.5 rounded text-2xs font-bold uppercase tracking-wider"
            >
              {{ room.is_active ? 'Activo' : 'Inactivo' }}
            </span>
          </div>

          <h3 class="mt-3 font-bold text-slate-900 text-base leading-snug">{{ room.name }}</h3>
          <p class="mt-1 text-xs text-slate-500 line-clamp-2">
            {{ room.description || 'Sin descripción de equipamiento o servicios.' }}
          </p>

          <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-2xs text-slate-400">
            <span class="flex items-center">
              <q-icon name="lock" size="14px" class="mr-1 text-teal-600" />
              Mutex Lock Activo
            </span>
            <span>ID: {{ room.id.substring(0, 8) }}...</span>
          </div>
        </div>

        <div v-if="can('rooms:manage')" class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
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

    <!-- Create / Edit Dialog -->
    <q-dialog v-model="showDialog">
      <q-card style="min-width: 440px; max-width: 520px; border-radius: 16px;">
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
              placeholder="Ej. Consultorio 1 - Ginecología General"
              filled
              required
            />
            <q-input
              v-model="form.room_number"
              label="Número / Identificador de Puerta *"
              placeholder="Ej. 101-A"
              filled
              required
            />
            <q-input
              v-model="form.description"
              label="Equipamiento y Detalles (Opcional)"
              placeholder="Ej. Camilla de exploración, ecógrafo 3D, lavamanos quirúrgico"
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
import { onMounted, reactive, ref } from 'vue'
import { Dialog, Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'

const { can, user } = useAcl()

const DEFAULT_CLINIC_ID = 'c1111111-1111-1111-1111-111111111111'
const clinicId = user.value?.clinicId || DEFAULT_CLINIC_ID

const rooms = ref([])
const loading = ref(false)
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formError = ref('')

const form = reactive({
  name: '',
  room_number: '',
  description: ''
})

async function fetchRooms () {
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.get(`/clinics/${clinicId}/rooms`, {
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
  form.description = ''
  formError.value = ''
  showDialog.value = true
}

function openEditDialog (room) {
  isEditing.value = true
  editingId.value = room.id
  form.name = room.name
  form.room_number = room.room_number || ''
  form.description = room.description || ''
  formError.value = ''
  showDialog.value = true
}

async function saveRoom () {
  submitting.value = true
  formError.value = ''
  try {
    const token = localStorage.getItem('access_token')
    if (isEditing.value) {
      await api.put(`/clinics/${clinicId}/rooms/${editingId.value}`, form, {
        headers: { Authorization: `Bearer ${token}` }
      })
      Notify.create({ type: 'positive', message: 'Consultorio actualizado exitosamente.' })
    } else {
      await api.post(`/clinics/${clinicId}/rooms`, form, {
        headers: { Authorization: `Bearer ${token}` }
      })
      Notify.create({ type: 'positive', message: 'Consultorio y cerradura Mutex creados exitosamente.' })
    }
    showDialog.value = false
    await fetchRooms()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Error al guardar consultorio.'
  } finally {
    submitting.value = false
  }
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
      await api.delete(`/clinics/${clinicId}/rooms/${room.id}`, {
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

onMounted(() => {
  fetchRooms()
})
</script>
