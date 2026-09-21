<template>
  <q-page class="p-4 sm:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-7xl mx-auto space-y-8">
      <!-- 1. Hero / Encabezado Principal del Directorio -->
      <div class="bg-gradient-to-r from-teal-800 via-teal-900 to-slate-900 rounded-3xl p-6 sm:p-10 text-white shadow-xl relative overflow-hidden">
        <div class="absolute -right-12 -bottom-12 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div class="relative z-10 max-w-3xl">
          <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-xs font-semibold mb-4 text-teal-200 border border-white/15">
            <img src="/icons/vitarecord-logo.png" alt="VitaRecord" class="w-4 h-4 rounded-full bg-white p-0.5 object-contain inline-block" />
            <span>Red Médica Certificada VitaRecord</span>
          </div>
          <h1 class="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Directorio Médico de Especialistas
          </h1>
          <p class="mt-2 text-sm sm:text-base text-teal-100/90 leading-relaxed">
            Encuentra a tu especialista de confianza, conoce en detalle su formación académica y trayectoria profesional, y reserva tu consulta médica en línea en cualquiera de nuestras sedes.
          </p>
        </div>
      </div>

      <!-- 2. Barra de Búsqueda y Filtros Interactivos -->
      <div class="bg-white p-5 sm:p-6 rounded-2xl shadow-sm border border-slate-200/80 space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-12 gap-4 items-center">
          <!-- Búsqueda por texto -->
          <div class="sm:col-span-5">
            <q-input
              v-model="searchQuery"
              placeholder="Buscar por nombre, especialidad o palabra clave..."
              outlined
              dense
              clearable
              class="rounded-xl"
              @update:model-value="applyFilters"
            >
              <template v-slot:prepend>
                <q-icon name="search" color="teal" />
              </template>
            </q-input>
          </div>

          <!-- Filtro por Clínica / Sede -->
          <div class="sm:col-span-4">
            <q-select
              v-model="selectedClinic"
              :options="clinicOptions"
              label="Filtrar por Sede / Clínica"
              outlined
              dense
              emit-value
              map-options
              class="rounded-xl"
              @update:model-value="applyFilters"
            >
              <template v-slot:prepend>
                <q-icon name="apartment" color="teal" />
              </template>
            </q-select>
          </div>

          <!-- Filtro por Especialidad -->
          <div class="sm:col-span-3">
            <q-select
              v-model="selectedSpecialty"
              :options="specialtyOptions"
              label="Especialidad"
              outlined
              dense
              emit-value
              map-options
              class="rounded-xl"
              @update:model-value="applyFilters"
            >
              <template v-slot:prepend>
                <q-icon name="medical_services" color="teal" />
              </template>
            </q-select>
          </div>
        </div>

        <!-- Indicador de resultados y reseteo -->
        <div class="flex flex-wrap items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-slate-800">{{ filteredDoctors.length }}</span>
            <span>especialistas verificados disponibles</span>
          </div>

          <q-btn
            v-if="searchQuery || selectedClinic || selectedSpecialty"
            flat
            dense
            color="primary"
            icon="clear_all"
            label="Limpiar filtros"
            no-caps
            class="text-xs"
            @click="clearFilters"
          />
        </div>
      </div>

      <!-- 3. Spinner de Carga -->
      <div v-if="loading" class="text-center py-16">
        <q-spinner-dots color="teal" size="56px" />
        <p class="text-xs text-slate-500 mt-3 font-medium">Consultando directorio médico certificado...</p>
      </div>

      <!-- 4. Mensaje si no hay resultados -->
      <div
        v-else-if="filteredDoctors.length === 0"
        class="bg-white p-12 rounded-2xl border border-slate-200 text-center max-w-lg mx-auto space-y-3"
      >
        <div class="w-16 h-16 rounded-full bg-teal-50 text-teal-600 flex items-center justify-center mx-auto">
          <q-icon name="person_search" size="32px" />
        </div>
        <h3 class="text-lg font-bold text-slate-900">No encontramos especialistas con esos filtros</h3>
        <p class="text-xs text-slate-500">
          Prueba cambiando la sede seleccionada o limpiando los términos de búsqueda para ver más médicos disponibles.
        </p>
        <q-btn
          outline
          color="primary"
          label="Restablecer filtros"
          no-caps
          class="font-semibold text-xs mt-2"
          @click="clearFilters"
        />
      </div>

      <!-- 5. Cuadrícula de Tarjetas de Médicos -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <q-card
          v-for="doctor in filteredDoctors"
          :key="doctor.id"
          class="bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow border border-slate-200/80 flex flex-col overflow-hidden"
        >
          <!-- Cabecera de la Tarjeta -->
          <div class="p-6 pb-4 flex items-start gap-4">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-teal-700 to-teal-500 text-white flex items-center justify-center font-bold text-xl shadow-sm shrink-0 overflow-hidden">
              <img
                v-if="doctor.profile_picture_url"
                :src="resolveApiUrl(doctor.profile_picture_url)"
                class="w-full h-full object-cover"
                alt="Foto doctor"
              />
              <span v-else>{{ getInitials(doctor.full_name) }}</span>
            </div>

            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5 mb-1">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-emerald-100 text-emerald-800">
                  <q-icon name="verified" size="12px" color="positive" />
                  VERIFICADO
                </span>
                <span v-if="doctor.license_number" class="text-3xs text-slate-400 font-mono">
                  {{ doctor.license_number }}
                </span>
              </div>

              <h2 class="text-base font-bold text-slate-900 truncate leading-snug">
                {{ doctor.full_name }}
              </h2>
              <div class="flex flex-wrap gap-1 mt-1">
                <template v-if="Array.isArray(doctor.specialties) && doctor.specialties.length > 0">
                  <q-badge
                    v-for="spec in doctor.specialties"
                    :key="spec"
                    color="teal-1"
                    text-color="teal-9"
                    class="text-3xs font-semibold py-0.5 px-2"
                  >
                    {{ spec }}
                  </q-badge>
                </template>
                <p v-else class="text-xs font-semibold text-teal-700 leading-tight">
                  {{ doctor.specialty || 'Especialista' }}
                </p>
              </div>
            </div>
          </div>

          <!-- Cuerpo: Extracto de Biografía y Sedes -->
          <div class="px-6 py-2 flex-1 space-y-3">
            <p class="text-xs text-slate-600 line-clamp-2 leading-relaxed">
              {{ doctor.biography || 'Especialista certificado con amplia vocación en atención integral y preventiva de salud.' }}
            </p>

            <!-- Sedes donde atiende -->
            <div class="space-y-1.5">
              <div class="text-3xs font-bold uppercase tracking-wider text-slate-400">
                Sedes de atención:
              </div>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="clinic in doctor.clinics"
                  :key="clinic.id"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-3xs font-medium bg-slate-100 text-slate-700 border border-slate-200/60 truncate max-w-full"
                >
                  <q-icon name="place" size="10px" color="teal" />
                  <span class="truncate">{{ clinic.name.split('(')[0].trim() }}</span>
                </span>
              </div>
            </div>

            <!-- Título académico destacado -->
            <div v-if="doctor.academic_degrees && doctor.academic_degrees.length > 0" class="pt-1">
              <div class="inline-flex items-center gap-1.5 text-2xs text-slate-700 bg-teal-50/70 p-2 rounded-lg border border-teal-100/80 w-full">
                <q-icon name="school" size="15px" color="teal" class="shrink-0" />
                <span class="truncate font-medium">
                  {{ doctor.academic_degrees[0].title }} • {{ doctor.academic_degrees[0].institution }}
                </span>
              </div>
            </div>
          </div>

          <!-- Acciones de la Tarjeta -->
          <div class="p-4 bg-slate-50/70 border-t border-slate-100 flex items-center gap-2">
            <q-btn
              outline
              color="slate-700"
              icon="school"
              label="Ver Perfil"
              no-caps
              class="flex-1 text-xs font-semibold py-1.5"
              @click="openDoctorDetails(doctor)"
            />

            <q-btn
              unelevated
              color="teal-8"
              icon="event_available"
              label="Agendar Cita"
              no-caps
              class="flex-1 text-xs font-bold py-1.5 shadow-sm"
              @click="bookWithDoctor(doctor)"
            />
          </div>
        </q-card>
      </div>
    </div>

    <!-- 6. Modal Detallado: Trayectoria Profesional y Títulos Académicos -->
    <q-dialog v-model="showDetailsModal">
      <q-card v-if="selectedDoctorDetails" class="w-full max-w-2xl rounded-3xl overflow-hidden shadow-2xl">
        <!-- Cabecera del Modal con Fondo Degradado -->
        <div class="bg-gradient-to-r from-teal-800 to-slate-900 p-6 text-white relative">
          <q-btn
            icon="close"
            flat
            round
            dense
            color="white"
            class="absolute top-4 right-4"
            @click="showDetailsModal = false"
          />

          <div class="flex items-center space-x-4">
            <div class="w-16 h-16 rounded-2xl bg-white text-teal-800 flex items-center justify-center font-bold text-2xl shadow-md shrink-0 overflow-hidden">
              <img
                v-if="selectedDoctorDetails.profile_picture_url"
                :src="resolveApiUrl(selectedDoctorDetails.profile_picture_url)"
                class="w-full h-full object-cover"
                alt="Foto doctor"
              />
              <span v-else>{{ getInitials(selectedDoctorDetails.full_name) }}</span>
            </div>

            <div>
              <div class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-2xs font-extrabold bg-emerald-100 text-emerald-900 mb-1">
                <q-icon name="verified" size="12px" color="positive" />
                MÉDICO VERIFICADO VITARECORD
              </div>
              <h2 class="text-xl font-bold leading-tight">{{ selectedDoctorDetails.full_name }}</h2>
              <div class="flex flex-wrap gap-1.5 mt-1.5">
                <template v-if="Array.isArray(selectedDoctorDetails.specialties) && selectedDoctorDetails.specialties.length > 0">
                  <q-badge
                    v-for="spec in selectedDoctorDetails.specialties"
                    :key="spec"
                    color="teal-8"
                    text-color="white"
                    class="text-xs font-medium py-1 px-2.5"
                  >
                    {{ spec }}
                  </q-badge>
                </template>
                <p v-else class="text-xs text-teal-200 font-medium">{{ selectedDoctorDetails.specialty || 'Especialista' }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Contenido del Modal con pestañas o secciones ordenadas -->
        <q-card-section class="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          <!-- Biografía -->
          <div>
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <q-icon name="account_box" size="16px" color="teal" />
              Presentación Profesional
            </h3>
            <p class="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100">
              {{ selectedDoctorDetails.biography || 'Profesional de la salud comprometido con la excelencia médica y el bienestar del paciente.' }}
            </p>
          </div>

          <!-- Títulos Universitarios y Certificaciones -->
          <div>
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <q-icon name="school" size="16px" color="teal" />
              Títulos Universitarios & Certificaciones
            </h3>

            <div v-if="selectedDoctorDetails.academic_degrees && selectedDoctorDetails.academic_degrees.length > 0" class="space-y-3">
              <div
                v-for="(degree, idx) in selectedDoctorDetails.academic_degrees"
                :key="idx"
                class="p-3.5 rounded-xl border border-slate-200 bg-white flex items-start justify-between gap-4"
              >
                <div>
                  <h4 class="text-sm font-bold text-slate-900">{{ degree.title }}</h4>
                  <p class="text-xs text-teal-700 font-medium">{{ degree.institution }}</p>
                  <p v-if="degree.license_or_id" class="text-3xs text-slate-400 font-mono mt-0.5">
                    Registro / Matrícula: {{ degree.license_or_id }}
                  </p>
                </div>
                <span v-if="degree.year" class="px-2.5 py-1 rounded-lg bg-teal-50 text-teal-800 font-bold text-xs">
                  {{ degree.year }}
                </span>
              </div>
            </div>
            <div v-else class="text-xs text-slate-400 italic p-3 bg-slate-50 rounded-xl">
              Sin títulos adicionales registrados.
            </div>
          </div>

          <!-- Experiencia Laboral e Institucional -->
          <div>
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <q-icon name="work" size="16px" color="teal" />
              Trayectoria y Experiencia Laboral
            </h3>

            <div v-if="selectedDoctorDetails.work_experience && selectedDoctorDetails.work_experience.length > 0" class="space-y-3">
              <div
                v-for="(exp, idx) in selectedDoctorDetails.work_experience"
                :key="idx"
                class="p-3.5 rounded-xl border border-slate-200 bg-white space-y-1.5"
              >
                <div class="flex items-start justify-between gap-2">
                  <div>
                    <h4 class="text-sm font-bold text-slate-900">{{ exp.position }}</h4>
                    <p class="text-xs font-medium text-slate-600">{{ exp.workplace }}</p>
                  </div>
                  <span class="px-2 py-0.5 rounded text-3xs font-semibold bg-slate-100 text-slate-700">
                    {{ exp.start_year || 'Inicio' }} — {{ exp.end_year ? exp.end_year : 'Actualidad' }}
                  </span>
                </div>
                <p v-if="exp.description" class="text-xs text-slate-500 leading-relaxed pt-1 border-t border-slate-100">
                  {{ exp.description }}
                </p>
              </div>
            </div>
            <div v-else class="text-xs text-slate-400 italic p-3 bg-slate-50 rounded-xl">
              Sin registros de experiencia previa documentados.
            </div>
          </div>

          <!-- Sedes de Consulta y Clínicas -->
          <div>
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <q-icon name="apartment" size="16px" color="teal" />
              Sedes de Consulta Habilitadas
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div
                v-for="clinic in selectedDoctorDetails.clinics"
                :key="clinic.id"
                class="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center gap-3"
              >
                <div class="w-8 h-8 rounded-lg bg-teal-100 text-teal-800 flex items-center justify-center shrink-0">
                  <q-icon name="location_city" size="18px" />
                </div>
                <div class="min-w-0">
                  <div class="text-xs font-bold text-slate-800 truncate">{{ clinic.name }}</div>
                  <div class="text-3xs text-slate-500">{{ clinic.timezone }} • Sede Activa</div>
                </div>
              </div>
            </div>
          </div>
        </q-card-section>

        <!-- Pie del Modal con Acción de Agendamiento -->
        <q-card-actions align="right" class="p-4 bg-slate-50 border-t border-slate-200">
          <q-btn flat label="Cerrar" color="slate-600" no-caps @click="showDetailsModal = false" />
          <q-btn
            unelevated
            color="teal-8"
            icon="event_available"
            label="Agendar Cita con este Especialista"
            no-caps
            class="font-bold px-4 py-2"
            @click="bookWithDoctor(selectedDoctorDetails)"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, resolveApiUrl } from 'boot/axios'

const router = useRouter()

const doctors = ref([])
const clinics = ref([])
const loading = ref(false)

const searchQuery = ref('')
const selectedClinic = ref(null)
const selectedSpecialty = ref(null)

const showDetailsModal = ref(false)
const selectedDoctorDetails = ref(null)

// Opciones de clínicas para el filtro
const clinicOptions = computed(() => {
  const options = [{ label: 'Todas las Sedes / Clínicas', value: null }]
  for (const c of clinics.value) {
    options.push({
      label: c.name,
      value: c.id
    })
  }
  return options
})

// Opciones de especialidades para el filtro
const specialtyOptions = computed(() => {
  const options = [{ label: 'Todas las Especialidades', value: null }]
  const set = new Set()
  for (const d of doctors.value) {
    if (Array.isArray(d.specialties)) {
      for (const s of d.specialties) {
        if (s) set.add(s)
      }
    }
    if (d.specialty) {
      d.specialty.split(',').forEach(s => {
        const trimmed = s.trim()
        if (trimmed) set.add(trimmed)
      })
    }
  }
  for (const spec of Array.from(set).sort()) {
    options.push({ label: spec, value: spec })
  }
  return options
})

// Médicos filtrados en memoria
const filteredDoctors = computed(() => {
  return doctors.value.filter(doc => {
    // Filtro clínica
    if (selectedClinic.value) {
      const worksAtClinic = (doc.clinics || []).some(c => c.id === selectedClinic.value)
      if (!worksAtClinic) return false
    }

    // Filtro especialidad
    if (selectedSpecialty.value) {
      const matchSpecialty = Array.isArray(doc.specialties) && doc.specialties.length > 0
        ? doc.specialties.includes(selectedSpecialty.value)
        : (doc.specialty || '').toLowerCase().includes(selectedSpecialty.value.toLowerCase())
      if (!matchSpecialty) return false
    }

    // Filtro texto libre
    if (searchQuery.value && searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase().trim()
      const inName = (doc.full_name || '').toLowerCase().includes(q)
      const inSpec = Array.isArray(doc.specialties)
        ? doc.specialties.some(s => (s || '').toLowerCase().includes(q))
        : (doc.specialty || '').toLowerCase().includes(q)
      const inBio = (doc.biography || '').toLowerCase().includes(q)
      const inClinic = (doc.clinics || []).some(c => c.name.toLowerCase().includes(q))
      if (!inName && !inSpec && !inBio && !inClinic) return false
    }

    return true
  })
})

function getInitials (name) {
  if (!name) return 'DR'
  const parts = name.replace(/^(Dr\.|Dra\.|Lic\.)\s*/i, '').trim().split(' ')
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

function openDoctorDetails (doc) {
  selectedDoctorDetails.value = doc
  showDetailsModal.value = true
}

function bookWithDoctor (doc) {
  const firstClinicId = doc.clinics?.[0]?.id || ''
  showDetailsModal.value = false
  router.push({
    path: '/book-appointment',
    query: {
      doctor_id: doc.id,
      clinic_id: firstClinicId
    }
  })
}

function clearFilters () {
  searchQuery.value = ''
  selectedClinic.value = null
  selectedSpecialty.value = null
}

function applyFilters () {
  // Las propiedades computadas reaccionan reactivamente
}

async function loadDirectoryData () {
  loading.value = true
  try {
    const [clinicsRes, docsRes] = await Promise.all([
      api.get('/clinics/public'),
      api.get('/doctors/public-directory')
    ])
    clinics.value = clinicsRes.data || []
    doctors.value = docsRes.data || []
  } catch (err) {
    console.error('Error al cargar directorio médico:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDirectoryData()
})
</script>
