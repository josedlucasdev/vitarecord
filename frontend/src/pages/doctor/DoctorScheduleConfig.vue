<template>
  <q-page class="p-6 max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div>
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold">
            <q-icon name="calendar_month" size="22px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">Configuración de Horario Semanal</h1>
            <p class="text-xs text-slate-500">
              Define los bloques de atención recurrente y la duración de cada turno médico.
            </p>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <q-btn
          outline
          color="primary"
          icon="refresh"
          label="Recargar"
          no-caps
          :loading="loading"
          @click="fetchSchedules"
        />
        <q-btn
          color="primary"
          icon="save"
          label="Guardar Horario"
          no-caps
          class="font-semibold"
          :loading="saving"
          @click="saveSchedule"
        />
      </div>
    </div>

    <!-- Alert / Domain Rule Info -->
    <div class="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3">
      <q-icon name="speed" color="blue" size="20px" class="mt-0.5" />
      <div class="text-xs text-blue-900">
        <span class="font-bold">Motor de Disponibilidad Transversal:</span> Al guardar tu horario semanal, el motor de turnos calcula y cachea dinámicamente en Redis (<code class="bg-blue-100 px-1 py-0.5 rounded font-mono">slots:{clinic_id}:{doctor_id}:{date}</code>) los slots disponibles para consulta rápida por pacientes y recepcionistas.
      </div>
    </div>

    <!-- Schedule Editor Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Blocks by Day of Week (2 Cols) -->
      <div class="lg:col-span-2 space-y-4">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-base font-bold text-slate-800">Bloques de Atención Semanales</h2>
            <q-btn
              flat
              dense
              color="primary"
              icon="add_circle"
              label="Agregar Bloque"
              no-caps
              class="font-semibold text-xs"
              @click="addBlock"
            />
          </div>

          <div v-if="blocks.length === 0" class="text-center p-8 border-2 border-dashed border-slate-200 rounded-xl space-y-2">
            <q-icon name="event_busy" size="36px" class="text-slate-300" />
            <div class="text-sm font-semibold text-slate-600">No hay bloques definidos</div>
            <p class="text-xs text-slate-400">Agrega bloques de horario para que los pacientes puedan agendar citas contigo.</p>
            <q-btn
              outline
              size="sm"
              color="primary"
              icon="add"
              label="Agregar Bloque Ahora"
              no-caps
              @click="addBlock"
            />
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="(b, idx) in blocks"
              :key="idx"
              class="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col md:flex-row items-center gap-3"
            >
              <!-- Day Select -->
              <div class="w-full md:w-44">
                <q-select
                  v-model="b.day_of_week"
                  :options="dayOptions"
                  emit-value
                  map-options
                  dense
                  outlined
                  bg-color="white"
                  label="Día de la Semana"
                />
              </div>

              <!-- Start Time -->
              <div class="w-full md:w-32">
                <q-input
                  v-model="b.start_time"
                  type="time"
                  dense
                  outlined
                  bg-color="white"
                  label="Inicio"
                />
              </div>

              <span class="text-slate-400 hidden md:inline">a</span>

              <!-- End Time -->
              <div class="w-full md:w-32">
                <q-input
                  v-model="b.end_time"
                  type="time"
                  dense
                  outlined
                  bg-color="white"
                  label="Fin"
                />
              </div>

              <!-- Slot Duration -->
              <div class="w-full md:w-36">
                <q-select
                  v-model="b.slot_duration_minutes"
                  :options="slotDurationOptions"
                  emit-value
                  map-options
                  dense
                  outlined
                  bg-color="white"
                  label="Duración Turno"
                />
              </div>

              <!-- Remove -->
              <q-btn
                flat
                round
                dense
                color="negative"
                icon="delete"
                @click="removeBlock(idx)"
              >
                <q-tooltip>Eliminar Bloque</q-tooltip>
              </q-btn>
            </div>
          </div>
        </div>
      </div>

      <!-- Live Slot Calculator Preview (1 Col) -->
      <div class="space-y-4">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
          <div class="flex items-center space-x-2">
            <q-icon name="preview" size="20px" class="text-teal-600" />
            <h2 class="text-base font-bold text-slate-800">Simulador de Disponibilidad</h2>
          </div>

          <p class="text-xs text-slate-500">
            Prueba cómo ven tus turnos los pacientes en una fecha específica consultando directamente la API / Redis.
          </p>

          <q-input
            v-model="previewDate"
            type="date"
            dense
            outlined
            label="Fecha a consultar"
            @update:model-value="fetchSlotsPreview"
          />

          <div v-if="loadingSlots" class="flex justify-center p-6">
            <q-spinner-dots color="primary" size="32px" />
          </div>

          <div v-else-if="previewSlots.length === 0" class="text-center p-6 bg-slate-50 rounded-xl border border-slate-200">
            <div class="text-xs text-slate-500">No hay turnos disponibles para esta fecha.</div>
            <div class="text-2xs text-slate-400 mt-1">Verifica si el día seleccionado coincide con tus bloques configurados.</div>
          </div>

          <div v-else class="space-y-2 max-h-80 overflow-y-auto pr-1">
            <div class="text-xs font-bold text-slate-600">
              {{ previewSlots.length }} Turnos generados:
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div
                v-for="(slot, idx) in previewSlots"
                :key="idx"
                class="p-2 rounded-lg bg-teal-50 border border-teal-200 text-teal-900 text-xs font-semibold text-center"
              >
                {{ slot.start_time }} - {{ slot.end_time }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'

const { user } = useAcl()

const DEFAULT_CLINIC_ID = 'c1111111-1111-1111-1111-111111111111'
const clinicId = user.value?.clinicId || DEFAULT_CLINIC_ID
const doctorId = user.value?.id || 'd1111111-1111-1111-1111-111111111111'

const loading = ref(false)
const saving = ref(false)
const blocks = ref([])

const dayOptions = [
  { label: 'Lunes', value: 0 },
  { label: 'Martes', value: 1 },
  { label: 'Miércoles', value: 2 },
  { label: 'Jueves', value: 3 },
  { label: 'Viernes', value: 4 },
  { label: 'Sábado', value: 5 },
  { label: 'Domingo', value: 6 }
]

const slotDurationOptions = [
  { label: '15 minutos', value: 15 },
  { label: '20 minutos', value: 20 },
  { label: '30 minutos', value: 30 },
  { label: '45 minutos', value: 45 },
  { label: '60 minutos', value: 60 }
]

// Live preview state
const previewDate = ref(new Date().toISOString().substring(0, 10))
const previewSlots = ref([])
const loadingSlots = ref(false)

function addBlock () {
  blocks.value.push({
    day_of_week: 0,
    start_time: '08:00',
    end_time: '13:00',
    slot_duration_minutes: 30
  })
}

function removeBlock (idx) {
  blocks.value.splice(idx, 1)
}

async function fetchSchedules () {
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.get(`/doctors/${doctorId}/schedules?clinic_id=${clinicId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    blocks.value = data.map(b => ({
      day_of_week: b.day_of_week,
      start_time: b.start_time,
      end_time: b.end_time,
      slot_duration_minutes: b.slot_duration_minutes
    }))
    if (blocks.value.length === 0) {
      // Valor por defecto amigable
      addBlock()
    }
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al cargar horarios del médico.'
    })
  } finally {
    loading.value = false
  }
}

async function saveSchedule () {
  saving.value = true
  try {
    const token = localStorage.getItem('access_token')
    await api.post(
      `/doctors/${doctorId}/schedules`,
      {
        clinic_id: clinicId,
        blocks: blocks.value
      },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    Notify.create({
      type: 'positive',
      message: 'Horarios guardados exitosamente. Caché de disponibilidad en Redis invalidada y actualizada.'
    })
    await fetchSlotsPreview()
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudo guardar la configuración de horarios.'
    })
  } finally {
    saving.value = false
  }
}

async function fetchSlotsPreview () {
  if (!previewDate.value) return
  loadingSlots.value = true
  try {
    const { data } = await api.get(`/clinics/${clinicId}/doctors/${doctorId}/slots?date=${previewDate.value}`)
    previewSlots.value = data
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al calcular slots disponibles.'
    })
  } finally {
    loadingSlots.value = false
  }
}

onMounted(async () => {
  await fetchSchedules()
  await fetchSlotsPreview()
})
</script>
