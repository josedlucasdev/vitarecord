<template>
  <q-page class="p-4 sm:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-5xl mx-auto space-y-6">
      <!-- 1. Encabezado del Perfil -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-xl shadow-sm">
            <q-icon name="badge" size="28px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">Mi Perfil Profesional y Presencia Pública</h1>
            <p class="text-xs text-slate-500">
              Gestiona tus títulos universitarios, experiencia laboral y biografía visibles en el Directorio Médico VitaRecord.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <q-btn
            outline
            color="teal-8"
            icon="visibility"
            label="Ver en Directorio"
            to="/doctors"
            target="_blank"
            no-caps
            class="text-xs font-semibold"
          />
          <q-btn
            unelevated
            color="primary"
            icon="save"
            label="Guardar Cambios"
            :loading="saving"
            no-caps
            class="text-xs font-bold shadow-sm"
            @click="saveProfile"
          />
        </div>
      </div>

      <div v-if="loading" class="text-center py-12">
        <q-spinner-dots color="teal" size="48px" />
        <p class="text-xs text-slate-500 mt-2">Cargando perfil profesional...</p>
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Columna Izquierda: Formulario Principal (2 Cols) -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Datos Generales y Biografía -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <q-icon name="person" color="teal" size="18px" />
              Información Profesional & Visibilidad
            </h2>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <q-input
                v-model="profile.full_name"
                label="Nombre Completo"
                outlined
                dense
                disable
                hint="Verificado con tu matrícula profesional"
              />
              <q-input
                v-model="profile.license_number"
                label="Matrícula / Registro Médico"
                outlined
                dense
                disable
                hint="Validado por Compliance VitaRecord"
              />
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <q-input
                v-model="profile.specialty"
                label="Especialidad Médica Principal"
                outlined
                dense
                placeholder="Ej. Ginecología & Obstetricia"
              />
              <q-input
                v-model="profile.phone"
                label="Teléfono de Contacto Profesional"
                outlined
                dense
                placeholder="+58 412 0000000"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Biografía / Resumen Profesional para Pacientes
              </label>
              <q-input
                v-model="profile.biography"
                type="textarea"
                rows="4"
                outlined
                dense
                counter
                maxlength="1000"
                placeholder="Describe tu enfoque clínico, trayectoria, áreas de interés y compromiso con la atención del paciente..."
              />
            </div>

            <div class="pt-2 border-t border-slate-100 flex items-center justify-between">
              <div>
                <div class="text-xs font-bold text-slate-800">Visibilidad en el Directorio Público</div>
                <div class="text-3xs text-slate-500">Permite que pacientes puedan encontrarte y agendar citas en línea</div>
              </div>
              <q-toggle v-model="profile.is_public_profile_enabled" color="teal" />
            </div>
          </div>

          <!-- Títulos Universitarios y Certificaciones -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <q-icon name="school" color="teal" size="18px" />
                Títulos Académicos & Certificaciones
              </h2>
              <q-btn
                unelevated
                size="sm"
                color="teal-8"
                icon="add"
                label="Agregar Título"
                no-caps
                @click="openAddDegreeModal"
              />
            </div>

            <div v-if="profile.academic_degrees && profile.academic_degrees.length > 0" class="space-y-3">
              <div
                v-for="(degree, idx) in profile.academic_degrees"
                :key="idx"
                class="p-4 rounded-xl border border-slate-200 bg-slate-50/60 flex items-start justify-between gap-3"
              >
                <div class="space-y-1">
                  <div class="font-bold text-sm text-slate-900">{{ degree.title }}</div>
                  <div class="text-xs text-teal-700 font-medium">{{ degree.institution }}</div>
                  <div class="text-3xs text-slate-500 flex items-center gap-3">
                    <span v-if="degree.year">Año: {{ degree.year }}</span>
                    <span v-if="degree.license_or_id">Registro: {{ degree.license_or_id }}</span>
                  </div>
                </div>
                <q-btn
                  flat
                  round
                  dense
                  color="negative"
                  icon="delete_outline"
                  size="sm"
                  @click="removeDegree(idx)"
                >
                  <q-tooltip>Eliminar titulación</q-tooltip>
                </q-btn>
              </div>
            </div>
            <div v-else class="text-xs text-slate-400 p-6 text-center border-2 border-dashed border-slate-200 rounded-xl">
              No has agregado títulos académicos. Haz clic en "Agregar Título" para registrar tus grados y diplomados.
            </div>
          </div>

          <!-- Experiencia Laboral e Institucional -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <q-icon name="work" color="teal" size="18px" />
                Trayectoria y Experiencia Laboral
              </h2>
              <q-btn
                unelevated
                size="sm"
                color="teal-8"
                icon="add"
                label="Agregar Experiencia"
                no-caps
                @click="openAddExperienceModal"
              />
            </div>

            <div v-if="profile.work_experience && profile.work_experience.length > 0" class="space-y-3">
              <div
                v-for="(exp, idx) in profile.work_experience"
                :key="idx"
                class="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2"
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <div class="font-bold text-sm text-slate-900">{{ exp.position }}</div>
                    <div class="text-xs text-slate-700 font-medium">{{ exp.workplace }}</div>
                    <div class="text-3xs text-slate-500 mt-0.5">
                      {{ exp.start_year || 'Inicio' }} — {{ exp.end_year ? exp.end_year : 'Actualidad' }}
                    </div>
                  </div>
                  <q-btn
                    flat
                    round
                    dense
                    color="negative"
                    icon="delete_outline"
                    size="sm"
                    @click="removeExperience(idx)"
                  >
                    <q-tooltip>Eliminar experiencia</q-tooltip>
                  </q-btn>
                </div>
                <p v-if="exp.description" class="text-xs text-slate-600 leading-relaxed pt-1 border-t border-slate-200/60">
                  {{ exp.description }}
                </p>
              </div>
            </div>
            <div v-else class="text-xs text-slate-400 p-6 text-center border-2 border-dashed border-slate-200 rounded-xl">
              No has documentado cargos o experiencia previa. Añade tu trayectoria para que los pacientes conozcan tu experiencia.
            </div>
          </div>
        </div>

        <!-- Columna Derecha: Vista Previa en Vivo (1 Col) -->
        <div class="space-y-6">
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4 sticky top-6">
            <div class="flex items-center justify-between">
              <h2 class="text-xs font-bold uppercase tracking-wider text-slate-500">
                Vista Previa de tu Tarjeta
              </h2>
              <span class="px-2 py-0.5 rounded text-3xs font-extrabold bg-teal-50 text-teal-700">
                En vivo
              </span>
            </div>

            <!-- Mock Card del Directorio -->
            <div class="p-5 rounded-2xl border border-slate-200 bg-slate-50/40 space-y-4 shadow-sm">
              <div class="flex items-start gap-3">
                <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-teal-700 to-teal-500 text-white flex items-center justify-center font-bold text-lg shadow-sm shrink-0">
                  DR
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-1 mb-0.5">
                    <span class="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded-full text-3xs font-extrabold bg-emerald-100 text-emerald-800">
                      <q-icon name="verified" size="10px" color="positive" />
                      VERIFICADO
                    </span>
                  </div>
                  <div class="text-sm font-bold text-slate-900 truncate">
                    {{ profile.full_name || 'Dr. Tu Nombre' }}
                  </div>
                  <div class="text-xs font-semibold text-teal-700">
                    {{ profile.specialty || 'Especialidad Médica' }}
                  </div>
                </div>
              </div>

              <p class="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                {{ profile.biography || 'Tu biografía y presentación médica aparecerán aquí ante los pacientes.' }}
              </p>

              <div v-if="profile.academic_degrees && profile.academic_degrees.length > 0" class="pt-1">
                <div class="inline-flex items-center gap-1.5 text-3xs text-slate-700 bg-teal-50 p-1.5 rounded-lg border border-teal-100 w-full truncate">
                  <q-icon name="school" size="14px" color="teal" />
                  <span class="truncate">{{ profile.academic_degrees[0].title }}</span>
                </div>
              </div>

              <div class="pt-2 border-t border-slate-200 flex gap-2">
                <q-btn outline dense color="slate-700" label="Ver Perfil" no-caps class="flex-1 text-2xs" />
                <q-btn unelevated dense color="teal-8" label="Agendar Cita" no-caps class="flex-1 text-2xs font-bold" />
              </div>
            </div>

            <div class="text-3xs text-slate-400 text-center leading-relaxed">
              Los cambios que guardes se reflejarán instantáneamente en el Directorio Médico VitaRecord.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Agregar Título -->
    <q-dialog v-model="showDegreeModal">
      <q-card class="w-full max-w-md rounded-2xl p-4">
        <q-card-section>
          <div class="text-base font-bold text-slate-900">Agregar Título Académico o Certificación</div>
          <div class="text-xs text-slate-500">Registra títulos de pregrado, posgrados o diplomados avalados.</div>
        </q-card-section>

        <q-card-section class="space-y-3">
          <q-input
            v-model="newDegree.title"
            label="Título o Grado Obtenido"
            outlined
            dense
            placeholder="Ej. Especialista en Ginecología"
          />
          <q-input
            v-model="newDegree.institution"
            label="Universidad o Institución Avalada"
            outlined
            dense
            placeholder="Ej. Universidad Central de Venezuela"
          />
          <div class="grid grid-cols-2 gap-2">
            <q-input
              v-model.number="newDegree.year"
              type="number"
              label="Año de Egreso"
              outlined
              dense
              placeholder="2018"
            />
            <q-input
              v-model="newDegree.license_or_id"
              label="N° Registro / Certificado"
              outlined
              dense
              placeholder="CMDF-1234"
            />
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancelar" color="slate-600" no-caps @click="showDegreeModal = false" />
          <q-btn unelevated color="teal-8" label="Agregar Titulación" no-caps class="font-bold" @click="addDegree" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Modal Agregar Experiencia -->
    <q-dialog v-model="showExperienceModal">
      <q-card class="w-full max-w-md rounded-2xl p-4">
        <q-card-section>
          <div class="text-base font-bold text-slate-900">Agregar Experiencia Laboral</div>
          <div class="text-xs text-slate-500">Documenta cargos hospitalarios, clínicas o jefaturas previas.</div>
        </q-card-section>

        <q-card-section class="space-y-3">
          <q-input
            v-model="newExp.position"
            label="Cargo o Rol Desempeñado"
            outlined
            dense
            placeholder="Ej. Cirujano Laparoscopista Adjunto"
          />
          <q-input
            v-model="newExp.workplace"
            label="Institución, Clínica u Hospital"
            outlined
            dense
            placeholder="Ej. Hospital Materno Infantil"
          />
          <div class="grid grid-cols-2 gap-2">
            <q-input
              v-model.number="newExp.start_year"
              type="number"
              label="Año de Inicio"
              outlined
              dense
              placeholder="2016"
            />
            <q-input
              v-model.number="newExp.end_year"
              type="number"
              label="Año de Fin (vacío = Actualidad)"
              outlined
              dense
              placeholder="2022"
            />
          </div>
          <q-input
            v-model="newExp.description"
            type="textarea"
            rows="2"
            label="Breve descripción de funciones o logros"
            outlined
            dense
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancelar" color="slate-600" no-caps @click="showExperienceModal = false" />
          <q-btn unelevated color="teal-8" label="Agregar Cargo" no-caps class="font-bold" @click="addExperience" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Notify } from 'quasar'
import { api } from 'boot/axios'

const loading = ref(true)
const saving = ref(false)

const profile = reactive({
  full_name: '',
  email: '',
  phone: '',
  specialty: '',
  biography: '',
  license_number: '',
  is_public_profile_enabled: true,
  academic_degrees: [],
  work_experience: []
})

const showDegreeModal = ref(false)
const newDegree = reactive({
  title: '',
  institution: '',
  year: null,
  license_or_id: ''
})

const showExperienceModal = ref(false)
const newExp = reactive({
  position: '',
  workplace: '',
  start_year: null,
  end_year: null,
  description: ''
})

function openAddDegreeModal () {
  newDegree.title = ''
  newDegree.institution = ''
  newDegree.year = new Date().getFullYear()
  newDegree.license_or_id = ''
  showDegreeModal.value = true
}

function addDegree () {
  if (!newDegree.title || !newDegree.institution) {
    Notify.create({ type: 'warning', message: 'Indica al menos el título y la institución.' })
    return
  }
  profile.academic_degrees.push({ ...newDegree })
  showDegreeModal.value = false
}

function removeDegree (index) {
  profile.academic_degrees.splice(index, 1)
}

function openAddExperienceModal () {
  newExp.position = ''
  newExp.workplace = ''
  newExp.start_year = new Date().getFullYear() - 3
  newExp.end_year = null
  newExp.description = ''
  showExperienceModal.value = true
}

function addExperience () {
  if (!newExp.position || !newExp.workplace) {
    Notify.create({ type: 'warning', message: 'Indica el cargo y el lugar de trabajo.' })
    return
  }
  profile.work_experience.push({ ...newExp })
  showExperienceModal.value = false
}

function removeExperience (index) {
  profile.work_experience.splice(index, 1)
}

async function loadMyProfile () {
  loading.value = true
  try {
    const { data } = await api.get('/doctors/me/profile')
    profile.full_name = data.full_name || ''
    profile.email = data.email || ''
    profile.phone = data.phone || ''
    profile.specialty = data.specialty || ''
    profile.biography = data.biography || ''
    profile.license_number = data.license_number || ''
    profile.is_public_profile_enabled = data.is_public_profile_enabled ?? true
    profile.academic_degrees = data.academic_degrees ? [...data.academic_degrees] : []
    profile.work_experience = data.work_experience ? [...data.work_experience] : []
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al cargar tu perfil profesional.' })
  } finally {
    loading.value = false
  }
}

async function saveProfile () {
  saving.value = true
  try {
    const payload = {
      biography: profile.biography,
      phone: profile.phone,
      specialty: profile.specialty,
      is_public_profile_enabled: profile.is_public_profile_enabled,
      academic_degrees: profile.academic_degrees,
      work_experience: profile.work_experience
    }
    await api.put('/doctors/me/profile', payload)
    Notify.create({
      type: 'positive',
      message: '¡Perfil profesional actualizado exitosamente en VitaRecord!'
    })
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al guardar cambios de perfil.'
    })
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadMyProfile()
})
</script>
