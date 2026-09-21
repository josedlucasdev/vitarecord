<template>
  <q-page class="p-4 md:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-7xl mx-auto space-y-6">
      <!-- Encabezado Principal -->
      <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center shadow-xs">
            <q-icon name="folder_shared" size="28px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900 leading-tight">Expedientes de Pacientes Atendidos</h1>
            <p class="text-xs text-slate-500">Búsqueda rápida de pacientes, consulta de historia médica integral e impresión oficial en PDF</p>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <q-btn
            flat
            color="primary"
            icon="refresh"
            label="Actualizar"
            no-caps
            class="text-xs font-semibold"
            :loading="loadingPatients"
            @click="fetchPatients"
          />
        </div>
      </div>

      <!-- Contenedor Master-Detail -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <!-- COLUMNA IZQUIERDA: Búsqueda y Lista de Pacientes (4 cols) -->
        <div class="lg:col-span-4 space-y-4">
          <div class="bg-white p-4 rounded-2xl shadow-xs border border-slate-200 space-y-3">
            <!-- Barra de Búsqueda -->
            <q-input
              v-model="searchQuery"
              outlined
              dense
              bg-color="slate-50"
              placeholder="Buscar por nombre, cédula, teléfono..."
              clearable
              debounce="350"
              @update:model-value="fetchPatients"
            >
              <template #prepend>
                <q-icon name="search" size="18px" color="slate-400" />
              </template>
            </q-input>

            <!-- Filtros Rápidos (Tabs / Chips) -->
            <div class="flex items-center space-x-1.5 pt-1">
              <q-btn
                v-for="opt in filterOptions"
                :key="opt.value"
                dense
                unelevated
                no-caps
                size="sm"
                :color="activeFilter === opt.value ? 'primary' : 'slate-100'"
                :text-color="activeFilter === opt.value ? 'white' : 'slate-700'"
                class="px-2.5 py-1 font-semibold rounded-lg text-xs"
                :label="opt.label"
                @click="setFilter(opt.value)"
              />
            </div>
          </div>

          <!-- Listado de Pacientes -->
          <div v-if="loadingPatients" class="p-8 text-center bg-white rounded-2xl border border-slate-200">
            <q-spinner-dots color="teal" size="36px" />
            <p class="text-slate-500 text-xs mt-2">Cargando pacientes atendidos...</p>
          </div>

          <div v-else-if="patients.length === 0" class="p-8 text-center bg-white rounded-2xl border border-slate-200 space-y-2">
            <q-icon name="person_search" size="36px" class="text-slate-300" />
            <div class="text-sm font-bold text-slate-700">Sin coincidencias</div>
            <p class="text-xs text-slate-500">
              {{ searchQuery ? 'No se encontraron pacientes que coincidan con la búsqueda.' : 'Aún no has atendido pacientes en la clínica.' }}
            </p>
          </div>

          <div v-else class="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
            <div
              v-for="p in patients"
              :key="getPatientKey(p)"
              class="p-3.5 rounded-xl border transition-all cursor-pointer flex items-center space-x-3"
              :class="isSelected(p) ? 'bg-teal-50/80 border-teal-500 shadow-sm ring-1 ring-teal-500' : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/70'"
              @click="selectPatient(p)"
            >
              <!-- Avatar -->
              <div class="relative shrink-0">
                <q-avatar size="44px" class="bg-teal-100 text-teal-800 font-bold text-sm shadow-xs border border-teal-200">
                  <img v-if="p.profile_picture_url" :src="p.profile_picture_url" alt="" />
                  <span v-else>{{ getInitials(p.full_name) }}</span>
                </q-avatar>
                <div
                  v-if="p.is_dependent"
                  class="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center text-3xs font-bold border-2 border-white"
                  title="Familiar Dependiente"
                >
                  <q-icon name="family_restroom" size="10px" />
                </div>
              </div>

              <!-- Información del Paciente -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-1">
                  <h4 class="text-xs font-bold text-slate-900 truncate leading-tight">{{ p.full_name }}</h4>
                  <span
                    class="text-3xs font-bold px-1.5 py-0.5 rounded"
                    :class="p.is_dependent ? 'bg-amber-100 text-amber-800' : 'bg-teal-100 text-teal-800'"
                  >
                    {{ p.is_dependent ? p.relationship : 'TITULAR' }}
                  </span>
                </div>

                <div class="text-2xs text-slate-500 truncate mt-0.5">
                  <span v-if="p.identification_number">CI: {{ p.identification_number }} • </span>
                  <span v-if="p.age !== null">{{ p.age }} años • </span>
                  <span v-if="p.blood_type" class="font-semibold text-rose-700">{{ p.blood_type }}</span>
                </div>

                <div class="flex items-center justify-between text-3xs text-slate-400 mt-1">
                  <span>{{ p.total_consultations }} consulta(s)</span>
                  <span v-if="p.last_consultation_at">{{ formatDate(p.last_consultation_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- COLUMNA DERECHA: Detalle del Paciente e Historia Médica Completa (8 cols) -->
        <div class="lg:col-span-8 space-y-5">
          <!-- Si no hay paciente seleccionado -->
          <div v-if="!selectedPatient" class="bg-white p-12 text-center rounded-2xl border border-slate-200 space-y-3">
            <div class="w-16 h-16 rounded-full bg-teal-50 text-teal-600 mx-auto flex items-center justify-center">
              <q-icon name="folder_open" size="32px" />
            </div>
            <h3 class="text-base font-bold text-slate-800">Selecciona un paciente</h3>
            <p class="text-xs text-slate-500 max-w-md mx-auto">
              Elige un paciente de la lista izquierda para consultar su ficha clínica permanente, antecedentes basales y cronología completa de consultas.
            </p>
          </div>

          <!-- Detalle del Paciente Seleccionado -->
          <div v-else class="space-y-5">
            <!-- Ficha Basal y Encabezado del Paciente -->
            <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-5">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
                <div class="flex items-center space-x-4">
                  <q-avatar size="56px" class="bg-teal-100 text-teal-800 font-bold text-lg shadow-xs border border-teal-200">
                    <img v-if="selectedPatient.profile_picture_url" :src="selectedPatient.profile_picture_url" alt="" />
                    <span v-else>{{ getInitials(selectedPatient.full_name) }}</span>
                  </q-avatar>

                  <div>
                    <div class="flex items-center space-x-2">
                      <h2 class="text-lg font-bold text-slate-900 leading-tight">{{ selectedPatient.full_name }}</h2>
                      <span
                        class="text-2xs font-bold px-2 py-0.5 rounded-full"
                        :class="selectedPatient.is_dependent ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'bg-teal-100 text-teal-900 border border-teal-300'"
                      >
                        {{ selectedPatient.is_dependent ? `Familiar: ${selectedPatient.relationship}` : 'Paciente Titular' }}
                      </span>
                    </div>

                    <p v-if="selectedPatient.is_dependent && selectedPatient.guardian_name" class="text-xs text-slate-500 mt-0.5">
                      <q-icon name="supervisor_account" size="14px" class="mr-1" />
                      Titular Responsable: <b>{{ selectedPatient.guardian_name }}</b>
                    </p>
                    <p v-else-if="selectedPatient.email" class="text-xs text-slate-500 mt-0.5">
                      <q-icon name="mail" size="14px" class="mr-1" />
                      {{ selectedPatient.email }}
                    </p>
                  </div>
                </div>

                <!-- Botón Principal: Imprimir PDF -->
                <div>
                  <q-btn
                    color="primary"
                    icon="print"
                    label="Imprimir Historia (PDF)"
                    no-caps
                    unelevated
                    class="font-bold text-xs px-4 py-2.5 rounded-xl shadow-xs"
                    :loading="downloadingPdf"
                    @click="downloadHistoryPdf"
                  >
                    <q-tooltip>Descarga o imprime el expediente clínico completo con formato oficial</q-tooltip>
                  </q-btn>
                </div>
              </div>

              <!-- Tarjetas de Datos Basales / Ficha Clínica -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div class="text-3xs uppercase font-bold text-slate-500">Identificación</div>
                  <div class="text-xs font-bold text-slate-900 mt-0.5">{{ selectedPatient.identification_number || 'No registrada' }}</div>
                </div>

                <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div class="text-3xs uppercase font-bold text-slate-500">Edad / Género</div>
                  <div class="text-xs font-bold text-slate-900 mt-0.5">
                    {{ selectedPatient.age !== null ? `${selectedPatient.age} años` : 'Sin edad' }}
                    <span v-if="selectedPatient.gender" class="text-slate-500 font-normal">({{ selectedPatient.gender }})</span>
                  </div>
                </div>

                <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div class="text-3xs uppercase font-bold text-slate-500">Grupo Sanguíneo</div>
                  <div class="text-xs font-bold text-rose-700 mt-0.5 flex items-center space-x-1">
                    <q-icon name="water_drop" size="14px" />
                    <span>{{ selectedPatient.blood_type || 'Sin registrar' }}</span>
                    <span v-if="selectedPatient.height_cm" class="text-slate-400 font-normal text-3xs">({{ selectedPatient.height_cm }} cm)</span>
                  </div>
                </div>

                <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div class="text-3xs uppercase font-bold text-slate-500">Teléfono</div>
                  <div class="text-xs font-bold text-slate-900 mt-0.5 truncate">{{ selectedPatient.phone || 'No registrado' }}</div>
                </div>
              </div>

              <!-- Alertas Médicas (Alergias y Antecedentes Crónicos) -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div
                  class="p-3 rounded-xl border flex items-start space-x-2.5"
                  :class="selectedPatient.allergies ? 'bg-rose-50/70 border-rose-200 text-rose-900' : 'bg-slate-50 border-slate-200 text-slate-700'"
                >
                  <q-icon
                    :name="selectedPatient.allergies ? 'warning' : 'check_circle'"
                    size="18px"
                    :class="selectedPatient.allergies ? 'text-rose-600' : 'text-slate-400'"
                    class="mt-0.5 shrink-0"
                  />
                  <div>
                    <div class="text-2xs font-bold uppercase tracking-wider">Alergias Conocidas</div>
                    <div class="text-xs mt-0.5 font-medium">{{ selectedPatient.allergies || 'Sin alergias registradas / No refiere' }}</div>
                  </div>
                </div>

                <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 flex items-start space-x-2.5">
                  <q-icon name="healing" size="18px" class="text-teal-600 mt-0.5 shrink-0" />
                  <div>
                    <div class="text-2xs font-bold uppercase tracking-wider text-slate-600">Condiciones / Antecedentes Crónicos</div>
                    <div class="text-xs mt-0.5 font-medium">{{ selectedPatient.chronic_conditions || 'Sin antecedentes reportados / No refiere' }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Listado Cronológico de Consultas -->
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-2">
                  <q-icon name="history_edu" size="18px" color="teal" />
                  <span>Historial de Atenciones Clínicas ({{ patientRecords.length }})</span>
                </h3>
              </div>

              <div v-if="loadingHistory" class="p-8 text-center bg-white rounded-2xl border border-slate-200">
                <q-spinner-dots color="teal" size="36px" />
                <p class="text-slate-500 text-xs mt-2">Descifrando historial clínico...</p>
              </div>

              <div v-else-if="patientRecords.length === 0" class="p-8 text-center bg-white rounded-2xl border border-slate-200 space-y-2">
                <q-icon name="info" size="32px" class="text-slate-300" />
                <p class="text-xs text-slate-500">No hay atenciones médicas finalizadas para este paciente.</p>
              </div>

              <div v-else class="space-y-4">
                <div
                  v-for="(rec, idx) in patientRecords"
                  :key="rec.id"
                  class="bg-white rounded-2xl shadow-xs border border-slate-200 overflow-hidden"
                >
                  <!-- Cabecera de la Consulta -->
                  <div class="bg-gradient-to-r from-teal-900 to-slate-900 text-white p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div class="flex items-center space-x-2.5">
                      <span class="w-6 h-6 rounded-full bg-teal-800 flex items-center justify-center text-xs font-bold border border-teal-600">
                        #{{ patientRecords.length - idx }}
                      </span>
                      <div>
                        <div class="font-bold text-xs leading-tight">{{ formatDate(rec.created_at) }}</div>
                        <div class="text-3xs text-teal-200">{{ rec.clinic_name || 'Clínica Principal' }}</div>
                      </div>
                    </div>

                    <div class="text-2xs text-teal-100 flex items-center space-x-2">
                      <span>Médico:</span>
                      <span class="font-bold bg-teal-800/80 px-2 py-0.5 rounded border border-teal-700">
                        Dr. {{ rec.doctor_name || 'Especialista' }}
                        <span v-if="rec.doctor_specialty" class="text-teal-300 font-normal">({{ rec.doctor_specialty }})</span>
                      </span>
                    </div>
                  </div>

                  <!-- Cuerpo de la Consulta -->
                  <div class="p-5 space-y-4">
                    <!-- Diagnóstico Principal y CIE-10 -->
                    <div class="bg-teal-50/60 p-3.5 rounded-xl border border-teal-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <div class="text-3xs uppercase font-bold text-teal-800 tracking-wider">Diagnóstico Principal</div>
                        <div class="text-xs font-bold text-teal-950 mt-0.5">{{ rec.diagnosis }}</div>
                      </div>
                      <div v-if="rec.icd10_code" class="self-start sm:self-auto">
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold bg-white text-teal-800 border border-teal-200">
                          CIE-10: {{ rec.icd10_code }}
                        </span>
                      </div>
                    </div>

                    <!-- Campos Clínicos: Anamnesis, Examen, Plan -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                      <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                        <div class="font-bold text-slate-700 flex items-center space-x-1 text-2xs uppercase tracking-wider">
                          <q-icon name="chat" size="13px" color="teal" />
                          <span>Anamnesis</span>
                        </div>
                        <p class="text-slate-600 whitespace-pre-line text-2xs leading-relaxed">{{ rec.anamnesis || 'No consignada.' }}</p>
                      </div>

                      <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                        <div class="font-bold text-slate-700 flex items-center space-x-1 text-2xs uppercase tracking-wider">
                          <q-icon name="monitor_heart" size="13px" color="teal" />
                          <span>Examen Físico</span>
                        </div>
                        <p class="text-slate-600 whitespace-pre-line text-2xs leading-relaxed">{{ rec.physical_exam || 'Sin hallazgos particulares.' }}</p>
                      </div>

                      <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                        <div class="font-bold text-slate-700 flex items-center space-x-1 text-2xs uppercase tracking-wider">
                          <q-icon name="assignment" size="13px" color="teal" />
                          <span>Plan Terapéutico</span>
                        </div>
                        <p class="text-slate-600 whitespace-pre-line text-2xs leading-relaxed">{{ rec.plan || 'No consignado.' }}</p>
                      </div>
                    </div>

                    <!-- Receta Médica Asociada -->
                    <div v-if="rec.prescriptions && rec.prescriptions.length > 0" class="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-100 space-y-2">
                      <div class="flex items-center justify-between">
                        <div class="font-bold text-xs text-emerald-950 flex items-center space-x-1.5">
                          <q-icon name="medication" size="16px" color="positive" />
                          <span>Prescripción Farmacológica (Receta)</span>
                        </div>
                        <span class="text-2xs font-mono font-bold text-emerald-800 bg-white px-2 py-0.5 rounded border border-emerald-200">
                          {{ rec.prescriptions[0].prescription_code }}
                        </span>
                      </div>

                      <div class="space-y-1.5">
                        <div
                          v-for="(itm, iIdx) in (rec.prescriptions[0].items || [])"
                          :key="iIdx"
                          class="p-2 rounded bg-white border border-emerald-100 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-1"
                        >
                          <div class="font-bold text-slate-800">
                            {{ itm.medication }} <span class="text-slate-500 font-normal">({{ itm.dosage }})</span>
                          </div>
                          <div class="text-2xs text-slate-600">
                            {{ itm.frequency }} • Duración: {{ itm.duration }}
                          </div>
                        </div>
                      </div>

                      <div class="pt-1 flex justify-end">
                        <q-btn
                          flat
                          dense
                          size="xs"
                          color="positive"
                          icon="download"
                          label="Descargar Receta Individual"
                          no-caps
                          class="font-bold"
                          @click="downloadPrescriptionPdf(rec.prescriptions[0].id)"
                        />
                      </div>
                    </div>

                    <!-- Anexos Médicos Adjuntos -->
                    <div v-if="rec.attachments && rec.attachments.length > 0" class="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                      <div class="font-bold text-xs text-slate-700 flex items-center space-x-1.5">
                        <q-icon name="attach_file" size="16px" color="teal" />
                        <span>Estudios y Anexos Clínicos ({{ rec.attachments.length }})</span>
                      </div>
                      <div class="flex flex-wrap gap-2">
                        <div
                          v-for="att in rec.attachments"
                          :key="att.id"
                          class="inline-flex items-center space-x-1.5 bg-white px-2.5 py-1 rounded-lg border border-slate-200 text-xs"
                        >
                          <q-icon name="description" size="14px" color="teal" />
                          <span class="font-medium text-slate-800 truncate max-w-xs">{{ att.file_name }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'

const $q = useQuasar()
const route = useRoute()

const loadingPatients = ref(false)
const loadingHistory = ref(false)
const downloadingPdf = ref(false)

const patients = ref([])
const selectedPatient = ref(null)
const patientRecords = ref([])

const searchQuery = ref('')
const activeFilter = ref('ALL')

const filterOptions = [
  { label: 'Todos', value: 'ALL' },
  { label: 'Titulares', value: 'TITULAR' },
  { label: 'Familiares', value: 'DEPENDENT' },
]

function getPatientKey(p) {
  return `${p.patient_id}_${p.dependent_id || 'titular'}`
}

function isSelected(p) {
  if (!selectedPatient.value) return false
  return (
    selectedPatient.value.patient_id === p.patient_id &&
    selectedPatient.value.dependent_id === p.dependent_id
  )
}

function setFilter(val) {
  activeFilter.value = val
  fetchPatients()
}

function getInitials(name) {
  if (!name) return 'P'
  const parts = name.trim().split(' ')
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('es-VE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

async function fetchPatients() {
  loadingPatients.value = true
  try {
    const params = {}
    if (searchQuery.value && searchQuery.value.trim()) {
      params.q = searchQuery.value.trim()
    }
    if (activeFilter.value !== 'ALL') {
      params.filter = activeFilter.value
    }
    const res = await api.get('/medical-records/doctor/my-patients', { params })
    patients.value = res.data

    // Si había un paciente seleccionado, mantenerlo o seleccionar el primero
    if (patients.value.length > 0) {
      if (selectedPatient.value) {
        const found = patients.value.find(
          p => p.patient_id === selectedPatient.value.patient_id && p.dependent_id === selectedPatient.value.dependent_id
        )
        if (found) {
          selectPatient(found)
          return
        }
      }
      selectPatient(patients.value[0])
    } else {
      selectedPatient.value = null
      patientRecords.value = []
    }
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: 'Error al cargar pacientes atendidos',
      caption: err.response?.data?.detail || err.message,
    })
  } finally {
    loadingPatients.value = false
  }
}

async function selectPatient(patient) {
  selectedPatient.value = patient
  loadingHistory.value = true
  try {
    const params = {}
    if (patient.dependent_id) {
      params.dependent_id = patient.dependent_id
    }
    const res = await api.get(`/medical-records/patient/${patient.patient_id}`, { params })
    patientRecords.value = res.data
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: 'Error al cargar la historia médica',
      caption: err.response?.data?.detail || err.message,
    })
  } finally {
    loadingHistory.value = false
  }
}

async function downloadHistoryPdf() {
  if (!selectedPatient.value) return
  downloadingPdf.value = true
  try {
    let url = `/medical-records/patient/${selectedPatient.value.patient_id}/pdf`
    if (selectedPatient.value.dependent_id) {
      url += `?dependent_id=${selectedPatient.value.dependent_id}`
    }
    const response = await api.get(url, { responseType: 'blob' })
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const blobUrl = window.URL.createObjectURL(blob)
    window.open(blobUrl, '_blank')
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: 'No se pudo generar la historia médica en PDF',
      caption: err.response?.data?.detail || err.message,
    })
  } finally {
    downloadingPdf.value = false
  }
}

async function downloadPrescriptionPdf(prescriptionId) {
  try {
    const response = await api.get(`/medical-records/prescriptions/${prescriptionId}/pdf`, {
      responseType: 'blob',
    })
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const blobUrl = window.URL.createObjectURL(blob)
    window.open(blobUrl, '_blank')
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: 'No se pudo descargar la receta médica',
      caption: err.response?.data?.detail || err.message,
    })
  }
}

onMounted(() => {
  fetchPatients()
})
</script>
