<template>
  <q-page class="p-6 max-w-5xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div>
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold">
            <q-icon name="event_available" size="22px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">Agendar Cita Médica</h1>
            <p class="text-xs text-slate-500">
              Reserva con garantía de bloqueo pesimista contra solapamientos de médico y sala física.
            </p>
          </div>
        </div>
      </div>

      <q-btn
        flat
        color="primary"
        icon="list_alt"
        label="Ver Mis Citas"
        to="/appointments/my-list"
        no-caps
        class="font-semibold"
      />
    </div>

    <!-- Booking Form Card -->
    <div class="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-200 space-y-6">
      <!-- 1. Beneficiario -->
      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
          1. ¿Para quién es la cita?
        </label>
        <div class="flex flex-wrap gap-3 items-center">
          <q-btn
            :outline="beneficiaryType !== 'self'"
            :color="beneficiaryType === 'self' ? 'primary' : 'grey-7'"
            icon="person"
            label="Para mí (Titular)"
            no-caps
            class="font-semibold"
            @click="selectSelf"
          />
          <q-btn
            :outline="beneficiaryType !== 'dependent'"
            :color="beneficiaryType === 'dependent' ? 'primary' : 'grey-7'"
            icon="family_restroom"
            label="Para un Familiar Dependiente"
            no-caps
            class="font-semibold"
            @click="selectDependentMode"
          />
          <q-btn
            v-if="beneficiaryType === 'dependent'"
            flat
            dense
            color="primary"
            icon="add"
            label="Registrar Nuevo Familiar"
            no-caps
            class="text-xs"
            @click="showAddDependentModal = true"
          />
        </div>

        <div v-if="beneficiaryType === 'dependent'" class="mt-4 max-w-md">
          <q-select
            v-model="selectedDependentId"
            :options="dependentOptions"
            emit-value
            map-options
            outlined
            dense
            label="Selecciona al Familiar"
            :loading="loadingDependents"
          />
        </div>
      </div>

      <q-separator />

      <!-- 2. Selección de Sede/Clínica, Especialista y Fecha -->
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">
            2. Selecciona Sede / Clínica, Médico y Fecha
          </label>

          <div class="flex items-center space-x-2">
            <!-- Modalidad de búsqueda -->
            <div class="inline-flex rounded-lg bg-slate-100 p-1 border border-slate-200 text-xs">
              <button
                type="button"
                :class="selectionFlow === 'byClinic' ? 'bg-white text-teal-700 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900 font-medium'"
                class="px-3 py-1 rounded-md transition-all flex items-center"
                @click="setFlow('byClinic')"
              >
                <q-icon name="apartment" size="14px" class="mr-1.5" />
                <span>Buscar por Sede / Clínica</span>
              </button>
              <button
                type="button"
                :class="selectionFlow === 'byDoctor' ? 'bg-white text-teal-700 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900 font-medium'"
                class="px-3 py-1 rounded-md transition-all flex items-center"
                @click="setFlow('byDoctor')"
              >
                <q-icon name="medical_services" size="14px" class="mr-1.5" />
                <span>Buscar por Médico Especialista</span>
              </button>
            </div>

            <q-btn
              flat
              round
              dense
              icon="refresh"
              color="teal"
              :loading="loadingClinics || loadingDoctors"
              @click="loadInitialData"
            >
              <q-tooltip>Refrescar sedes y especialistas</q-tooltip>
            </q-btn>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- 1. Clínica / Sede -->
          <div>
            <q-select
              v-model="selectedClinicId"
              :options="clinicOptions"
              :loading="loadingClinics"
              no-data-label="No hay sedes disponibles"
              emit-value
              map-options
              outlined
              label="Clínica / Sede de Atención *"
              @update:model-value="onClinicChanged"
            >
              <template v-slot:prepend>
                <q-icon name="apartment" color="teal" />
              </template>
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section avatar>
                    <q-icon name="apartment" color="teal" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="font-medium">{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption class="text-xs text-slate-500">
                      {{ scope.opt.caption || 'Sede de Atención' }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>

          <!-- 2. Especialista Médico -->
          <div>
            <q-select
              v-model="selectedDoctorId"
              :options="doctorOptions"
              :loading="loadingDoctors"
              no-data-label="No se encontraron médicos para esta sede"
              emit-value
              map-options
              outlined
              label="Especialista Médico *"
              @update:model-value="onDoctorChanged"
            >
              <template v-slot:prepend>
                <q-icon name="medical_services" color="teal" />
              </template>
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section avatar>
                    <q-avatar size="30px" color="teal-1" text-color="teal-800" icon="person" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="font-medium">{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption class="text-xs text-slate-500">
                      {{ scope.opt.specialty }} • Atiende en {{ scope.opt.clinicsCount }} sede(s)
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>

          <!-- 3. Fecha de Consulta -->
          <div>
            <q-input
              v-model="selectedDate"
              type="date"
              outlined
              label="Fecha de la Consulta *"
              @update:model-value="loadAvailableSlots"
            >
              <template v-slot:prepend>
                <q-icon name="event" color="teal" />
              </template>
            </q-input>
          </div>
        </div>

        <!-- Feedback contextual de la sede y especialista -->
        <div v-if="selectedDoctor && selectedClinic" class="p-3 bg-teal-50/80 border border-teal-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between text-xs text-teal-900 gap-2">
          <div class="flex items-center space-x-2">
            <q-icon name="check_circle" size="18px" color="teal" />
            <span>
              Consultando turnos en <strong>{{ selectedClinic.name }}</strong> con el especialista <strong>{{ selectedDoctor.full_name }}</strong> ({{ selectedDoctor.specialty }}).
            </span>
          </div>
          <div v-if="selectedDoctor.clinics && selectedDoctor.clinics.length > 1" class="text-2xs text-teal-800 bg-teal-100/90 px-2.5 py-1 rounded-full font-semibold">
            Este médico atiende en {{ selectedDoctor.clinics.length }} sedes diferentes
          </div>
        </div>
      </div>

      <q-separator />

      <!-- 3. Slots Disponibles (Redis) -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">
            3. Turnos Disponibles en Vivo (Aceleración Redis)
          </label>
          <span v-if="loadingSlots" class="text-xs text-slate-400 flex items-center">
            <q-spinner size="14px" class="mr-1" /> Calculando...
          </span>
        </div>

        <div v-if="slots.length === 0" class="p-6 bg-slate-50 rounded-xl border border-slate-200 text-center">
          <q-icon name="schedule" size="32px" class="text-slate-300" />
          <div class="text-xs text-slate-500 mt-2 font-medium">
            No hay turnos disponibles para la fecha seleccionada.
          </div>
          <div class="text-2xs text-slate-400 mt-1">
            Verifica que el médico tenga horario configurado ese día de la semana.
          </div>
        </div>

        <div v-else class="space-y-3">
          <!-- Indicador / Leyenda de disponibilidad -->
          <div class="flex items-center space-x-4 text-2xs text-slate-500 font-medium">
            <div class="flex items-center space-x-1.5">
              <span class="w-3 h-3 rounded-md bg-white border border-slate-300 inline-block shadow-2xs"></span>
              <span>Disponible</span>
            </div>
            <div class="flex items-center space-x-1.5">
              <span class="w-3 h-3 rounded-md bg-teal-600 inline-block"></span>
              <span>Seleccionado</span>
            </div>
            <div class="flex items-center space-x-1.5">
              <span class="w-3 h-3 rounded-md bg-slate-200 border border-slate-300 opacity-60 inline-block"></span>
              <span>Ocupado</span>
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
            <button
              type="button"
              v-for="(slot, idx) in slots"
              :key="idx"
              :disabled="!slot.is_available"
              :class="[
                'p-3 rounded-xl border text-center transition-all font-semibold text-xs select-none',
                !slot.is_available
                  ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed opacity-60'
                  : selectedSlot === slot
                    ? 'bg-teal-600 text-white border-teal-700 shadow-sm scale-105 cursor-pointer ring-2 ring-teal-400 ring-offset-1'
                    : 'bg-white hover:bg-teal-50 text-slate-800 border-slate-200 cursor-pointer'
              ]"
              @click="slot.is_available ? (selectedSlot = slot) : null"
            >
              <div class="flex items-center justify-center space-x-1">
                <span>{{ slot.start_time }}</span>
                <q-icon v-if="!slot.is_available" name="lock" size="12px" class="text-slate-400" />
              </div>
              <div class="text-2xs font-normal" :class="slot.is_available ? 'opacity-75' : 'text-slate-400'">
                {{ slot.is_available ? `a ${slot.end_time}` : 'Ocupado' }}
              </div>
            </button>
          </div>
        </div>
      </div>

      <q-separator />

      <!-- 4. Motivo y Confirmación -->
      <div class="space-y-4">
        <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">
          4. Motivo de Consulta y Confirmación
        </label>

        <q-input
          v-model="reason"
          outlined
          label="Motivo de la consulta médica (opcional)"
          placeholder="Ej. Chequeo anual, dolor pélvico recurrente, control ginecológico"
          type="textarea"
          rows="2"
        />

        <div v-if="bookingError" class="p-3 bg-red-50 text-red-700 text-xs rounded-xl flex items-center">
          <q-icon name="warning" size="18px" class="mr-2" />
          <span>{{ bookingError }}</span>
        </div>

        <div class="pt-2 flex justify-end">
          <q-btn
            color="primary"
            icon="check_circle"
            label="Confirmar y Agendar Cita"
            no-caps
            class="px-6 py-3 font-bold text-sm shadow-md"
            :loading="submitting"
            :disable="!selectedSlot || !selectedSlot.is_available"
            @click="submitBooking"
          />
        </div>
      </div>
    </div>

    <!-- Modal Registrar Familiar -->
    <q-dialog v-model="showAddDependentModal">
      <q-card style="min-width: 400px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-teal-700 to-cyan-800 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="person_add" size="22px" />
            <h3 class="text-base font-bold">Registrar Familiar Dependiente</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6 space-y-4">
          <form class="space-y-3" @submit.prevent="saveDependent">
            <q-input v-model="depForm.full_name" label="Nombre Completo *" filled required />
            <q-select
              v-model="depForm.relationship"
              :options="['HIJO', 'PADRE', 'CONYUGE', 'OTRO']"
              label="Parentesco *"
              filled
              required
            />
            <q-input v-model="depForm.birth_date" label="Fecha de Nacimiento *" type="date" filled required />
            <q-select v-model="depForm.gender" :options="['F', 'M']" label="Género (Opcional)" filled />
            <q-input v-model="depForm.id_document" label="Documento / Cédula (Opcional)" filled />

            <div class="pt-2 flex justify-end space-x-2">
              <q-btn flat label="Cancelar" v-close-popup no-caps />
              <q-btn type="submit" color="primary" label="Guardar Familiar" no-caps class="font-semibold" />
            </div>
          </form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'

const router = useRouter()
const route = useRoute()
const { user } = useAcl()

const DEFAULT_CLINIC_ID = 'c1111111-1111-1111-1111-111111111111'

// 1. Modalidad de Selección y Estado Principal
const selectionFlow = ref('byClinic') // 'byClinic' | 'byDoctor'

const clinics = ref([])
const selectedClinicId = ref(user.value?.clinicId || DEFAULT_CLINIC_ID)
const loadingClinics = ref(false)

const allDoctors = ref([])
const selectedDoctorId = ref(null)
const loadingDoctors = ref(false)

const selectedDate = ref(new Date().toISOString().substring(0, 10))

const slots = ref([])
const loadingSlots = ref(false)
const selectedSlot = ref(null)

const reason = ref('')
const submitting = ref(false)
const bookingError = ref('')

// Dependientes familiares
const beneficiaryType = ref('self')
const selectedDependentId = ref(null)
const dependentOptions = ref([])
const loadingDependents = ref(false)
const showAddDependentModal = ref(false)

const depForm = reactive({
  full_name: '',
  relationship: 'HIJO',
  birth_date: '',
  gender: 'F',
  id_document: ''
})

function setFlow (flow) {
  selectionFlow.value = flow
}

// Entidades reactivas seleccionadas
const selectedClinic = computed(() => {
  return clinics.value.find(c => c.id === selectedClinicId.value) || null
})

const selectedDoctor = computed(() => {
  return allDoctors.value.find(d => d.id === selectedDoctorId.value) || null
})

// Opciones calculadas de clínicas según flujo (con deduplicación estricta por ID)
const clinicOptions = computed(() => {
  let list = clinics.value
  if (selectionFlow.value === 'byDoctor' && selectedDoctor.value?.clinics?.length) {
    list = selectedDoctor.value.clinics
  }
  const seen = new Set()
  const unique = []
  for (const c of list) {
    if (c?.id && !seen.has(c.id)) {
      seen.add(c.id)
      unique.push(c)
    }
  }
  return unique.map(c => ({
    label: c.name,
    value: c.id,
    caption: `${c.timezone || 'America/Caracas'} • ${c.country_code || 'VE'}`
  }))
})

// Opciones calculadas de doctores según flujo (con deduplicación estricta por ID)
const doctorOptions = computed(() => {
  let list = allDoctors.value
  if (selectionFlow.value === 'byClinic' && selectedClinicId.value) {
    list = allDoctors.value.filter(d => (d.clinics || []).some(c => c.id === selectedClinicId.value))
  }
  const seen = new Set()
  const unique = []
  for (const d of list) {
    if (d?.id && !seen.has(d.id)) {
      seen.add(d.id)
      unique.push(d)
    }
  }
  return unique.map(d => ({
    label: `${d.full_name || d.email}`,
    specialty: d.specialty || 'Medicina Especializada',
    clinicsCount: (d.clinics || []).length,
    value: d.id
  }))
})

async function onClinicChanged (newClinicId) {
  selectedClinicId.value = newClinicId

  // Si estamos navegando por clínica, verificar si el médico seleccionado sigue siendo válido
  if (selectionFlow.value === 'byClinic') {
    const validDoctor = doctorOptions.value.some(d => d.value === selectedDoctorId.value)
    if (!validDoctor && doctorOptions.value.length > 0) {
      selectedDoctorId.value = doctorOptions.value[0].value
    }
  }
  await loadAvailableSlots()
}

async function onDoctorChanged (newDoctorId) {
  selectedDoctorId.value = newDoctorId

  // Si estamos navegando por médico, asegurar que la clínica elegida es una donde atiende el médico
  if (selectionFlow.value === 'byDoctor') {
    const doc = allDoctors.value.find(d => d.id === newDoctorId)
    if (doc?.clinics?.length) {
      const validClinic = doc.clinics.some(c => c.id === selectedClinicId.value)
      if (!validClinic) {
        selectedClinicId.value = doc.clinics[0].id
      }
    }
  }
  await loadAvailableSlots()
}

async function loadInitialData () {
  loadingClinics.value = true
  loadingDoctors.value = true
  try {
    const [clinicsRes, doctorsRes] = await Promise.all([
      api.get('/clinics', { params: { _t: Date.now() } }),
      api.get('/doctors', { params: { _t: Date.now() } })
    ])
    clinics.value = clinicsRes.data
    allDoctors.value = doctorsRes.data

    // Manejar pre-selección desde query params (ej. desde el Directorio Médico Público)
    const queryDoctorId = route.query?.doctor_id
    const queryClinicId = route.query?.clinic_id

    if (queryDoctorId && allDoctors.value.some(d => d.id === queryDoctorId)) {
      selectedDoctorId.value = queryDoctorId
      selectionFlow.value = 'byDoctor'

      const targetDoc = allDoctors.value.find(d => d.id === queryDoctorId)
      if (queryClinicId && clinics.value.some(c => c.id === queryClinicId)) {
        selectedClinicId.value = queryClinicId
      } else if (targetDoc?.clinics?.length) {
        selectedClinicId.value = targetDoc.clinics[0].id
      }
    } else {
      // Inicializar clínica seleccionada por defecto
      if (queryClinicId && clinics.value.some(c => c.id === queryClinicId)) {
        selectedClinicId.value = queryClinicId
      } else if (clinics.value.length > 0) {
        const match = clinics.value.find(c => c.id === selectedClinicId.value)
        if (!match) {
          selectedClinicId.value = clinics.value[0].id
        }
      }

      // Inicializar médico seleccionado
      if (allDoctors.value.length > 0 && !selectedDoctorId.value) {
        const docsInClinic = allDoctors.value.filter(d => (d.clinics || []).some(c => c.id === selectedClinicId.value))
        selectedDoctorId.value = docsInClinic.length > 0 ? docsInClinic[0].id : allDoctors.value[0].id
      }
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al consultar clínicas y médicos disponibles.' })
  } finally {
    loadingClinics.value = false
    loadingDoctors.value = false
    await loadAvailableSlots()
  }
}

function selectSelf () {
  beneficiaryType.value = 'self'
  selectedDependentId.value = null
}

function selectDependentMode () {
  beneficiaryType.value = 'dependent'
  fetchDependents()
}

async function fetchDependents () {
  loadingDependents.value = true
  try {
    const { data } = await api.get('/patients/me/dependents')
    dependentOptions.value = data.map(d => ({
      label: `${d.full_name} (${d.relationship}) ${d.is_emancipated ? '• Emancipado' : ''}`,
      value: d.id
    }))
    if (dependentOptions.value.length > 0 && !selectedDependentId.value) {
      selectedDependentId.value = dependentOptions.value[0].value
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al cargar familiares.' })
  } finally {
    loadingDependents.value = false
  }
}

async function saveDependent () {
  try {
    const { data } = await api.post('/patients/me/dependents', depForm)
    Notify.create({ type: 'positive', message: 'Familiar registrado correctamente.' })
    showAddDependentModal.value = false
    await fetchDependents()
    selectedDependentId.value = data.id
  } catch (err) {
    Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Error al guardar familiar.' })
  }
}

async function loadAvailableSlots () {
  if (!selectedClinicId.value || !selectedDoctorId.value || !selectedDate.value) {
    slots.value = []
    return
  }
  loadingSlots.value = true
  selectedSlot.value = null
  bookingError.value = ''
  try {
    const { data } = await api.get(`/clinics/${selectedClinicId.value}/doctors/${selectedDoctorId.value}/slots?date=${selectedDate.value}`)
    slots.value = data
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al consultar disponibilidad en Redis.' })
  } finally {
    loadingSlots.value = false
  }
}

async function submitBooking () {
  if (!selectedSlot.value || !selectedSlot.value.is_available) return
  submitting.value = true
  bookingError.value = ''

  let appointmentCreated = false
  try {
    const startIso = `${selectedDate.value}T${selectedSlot.value.start_time}:00`
    const endIso = `${selectedDate.value}T${selectedSlot.value.end_time}:00`

    const payload = {
      clinic_id: selectedClinicId.value,
      doctor_id: selectedDoctorId.value,
      dependent_id: beneficiaryType.value === 'dependent' ? selectedDependentId.value : undefined,
      start_time: startIso,
      end_time: endIso,
      reason: reason.value || undefined,
      estimated_amount: 35.00
    }

    await api.post('/appointments', payload)
    appointmentCreated = true

    Notify.create({
      type: 'positive',
      message: '¡Cita médica agendada exitosamente! Se generó el registro de cobro inicial en UNPAID.'
    })
  } catch (err) {
    if (!appointmentCreated) {
      bookingError.value = err.response?.data?.detail || err.message || 'No se pudo completar la reserva.'
      return
    }
  } finally {
    submitting.value = false
  }

  if (appointmentCreated) {
    try {
      await router.push('/appointments/my-list')
    } catch {
      // Ignorar redirección abortada si ya está en navegación
    }
  }
}

onMounted(async () => {
  await loadInitialData()
})
</script>
