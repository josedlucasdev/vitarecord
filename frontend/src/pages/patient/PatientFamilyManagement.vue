<template>
  <q-page class="p-4 sm:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-6xl mx-auto space-y-6">
      <!-- 1. Encabezado -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center space-x-3.5">
          <div class="w-12 h-12 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-xl shadow-sm">
            <q-icon name="family_restroom" size="28px" />
          </div>
          <div>
            <div class="flex items-center gap-2.5">
              <h1 class="text-xl font-bold text-slate-900 leading-tight">Mi Núcleo Familiar</h1>
              <span class="text-xs px-2.5 py-0.5 rounded-full font-bold bg-teal-50 text-teal-800 border border-teal-200">
                {{ dependents.length }} {{ dependents.length === 1 ? 'Familiar' : 'Familiares' }}
              </span>
            </div>
            <p class="text-xs text-slate-500 mt-0.5">
              Gestiona los datos personales, fotografías y fichas clínicas de tus dependientes para agendar sus consultas fácilmente.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2 self-end sm:self-center">
          <q-btn
            outline
            color="teal-8"
            icon="person"
            label="Mi Perfil de Salud"
            to="/patient/profile"
            no-caps
            class="text-xs font-semibold"
          />
          <q-btn
            unelevated
            color="primary"
            icon="person_add"
            label="Agregar Familiar"
            no-caps
            class="text-xs font-bold shadow-sm px-4 py-2"
            @click="openCreateModal"
          />
        </div>
      </div>

      <!-- Estado de Carga -->
      <div v-if="loading" class="text-center py-16">
        <q-spinner-dots color="teal" size="48px" />
        <p class="text-xs text-slate-500 mt-2">Cargando a los miembros de tu familia...</p>
      </div>

      <!-- Estado Vacío -->
      <div
        v-else-if="dependents.length === 0"
        class="bg-white rounded-2xl p-12 text-center border-2 border-dashed border-slate-200 shadow-xs max-w-lg mx-auto space-y-4"
      >
        <div class="w-16 h-16 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center mx-auto">
          <q-icon name="group_add" size="36px" />
        </div>
        <div class="space-y-1">
          <h2 class="text-base font-bold text-slate-800 m-0">Aún no tienes familiares registrados</h2>
          <p class="text-xs text-slate-500 leading-relaxed max-w-sm mx-auto">
            Registra a tus hijos, cónyuge o padres. Podrás agendar citas para ellos, mantener su ficha médica actualizada y acceder a sus recetas.
          </p>
        </div>
        <q-btn
          unelevated
          color="primary"
          icon="person_add"
          label="Registrar Primer Familiar"
          no-caps
          class="text-xs font-bold px-5 py-2.5 shadow-sm"
          @click="openCreateModal"
        />
      </div>

      <!-- Grid de Tarjetas de Familiares -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <div
          v-for="dep in dependents"
          :key="dep.id"
          class="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all flex flex-col justify-between overflow-hidden"
        >
          <!-- Parte Superior de la Tarjeta -->
          <div class="p-5 space-y-4">
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center space-x-3">
                <!-- Avatar o Foto -->
                <div class="relative group shrink-0">
                  <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-teal-700 to-teal-500 text-white flex items-center justify-center font-bold text-lg shadow-sm overflow-hidden border border-slate-100">
                    <img
                      v-if="dep.profile_picture_url"
                      :src="getResolvedAvatarUrl(dep.profile_picture_url)"
                      class="w-full h-full object-cover"
                      alt="Foto familiar"
                    />
                    <span v-else>{{ getInitials(dep.full_name) }}</span>
                  </div>
                </div>

                <div>
                  <h2 class="text-sm font-black text-slate-900 leading-snug line-clamp-1 m-0">
                    {{ dep.full_name }}
                  </h2>
                  <div class="flex items-center gap-1.5 mt-1">
                    <span
                      class="text-3xs px-2 py-0.5 rounded-md font-bold uppercase tracking-wider"
                      :class="getRelationshipBadgeClass(dep.relationship)"
                    >
                      {{ formatRelationship(dep.relationship) }}
                    </span>
                    <span v-if="dep.age != null" class="text-2xs font-semibold text-slate-500">
                      • {{ dep.age }} {{ dep.age === 1 ? 'año' : 'años' }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Menú de Acciones Rápidas -->
              <q-btn flat round dense icon="more_vert" color="slate-6" size="sm">
                <q-menu auto-close>
                  <q-list dense style="min-width: 140px">
                    <q-item clickable @click="openEditModal(dep)">
                      <q-item-section avatar><q-icon name="edit" size="16px" color="teal" /></q-item-section>
                      <q-item-section class="text-xs">Editar Ficha</q-item-section>
                    </q-item>
                    <q-item clickable @click="bookAppointmentFor(dep)">
                      <q-item-section avatar><q-icon name="calendar_today" size="16px" color="teal" /></q-item-section>
                      <q-item-section class="text-xs">Agendar Cita</q-item-section>
                    </q-item>
                    <q-separator />
                    <q-item clickable class="text-red-700" @click="confirmDelete(dep)">
                      <q-item-section avatar><q-icon name="delete" size="16px" color="red" /></q-item-section>
                      <q-item-section class="text-xs">Eliminar</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-btn>
            </div>

            <!-- Datos de Identidad -->
            <div class="text-2xs text-slate-500 space-y-1 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
              <div class="flex items-center justify-between">
                <span>Documento / Cédula:</span>
                <strong class="text-slate-700">{{ dep.id_document || 'No registrado' }}</strong>
              </div>
              <div class="flex items-center justify-between">
                <span>Nacimiento:</span>
                <strong class="text-slate-700">{{ dep.birth_date }}</strong>
              </div>
              <div v-if="dep.gender" class="flex items-center justify-between">
                <span>Sexo:</span>
                <strong class="text-slate-700">{{ dep.gender }}</strong>
              </div>
              <div v-if="dep.phone" class="flex items-center justify-between">
                <span>Teléfono:</span>
                <strong class="text-slate-700">{{ dep.phone }}</strong>
              </div>
            </div>

            <!-- Mini Ficha Clínica Permanente -->
            <div class="space-y-2">
              <div class="text-3xs uppercase tracking-wider font-bold text-slate-400 flex items-center justify-between">
                <span>Ficha Clínica Permanente</span>
                <span
                  v-if="dep.is_profile_complete"
                  class="text-emerald-700 font-bold flex items-center"
                >
                  <q-icon name="check" size="11px" class="mr-0.5" /> Completa
                </span>
                <span v-else class="text-amber-700 font-bold">Incompleta</span>
              </div>

              <div class="grid grid-cols-2 gap-2 text-2xs">
                <div class="bg-teal-50/70 border border-teal-200/80 p-2 rounded-xl">
                  <div class="text-3xs text-teal-800 font-bold">🩸 Grupo Sanguíneo</div>
                  <div class="font-black text-slate-800 mt-0.5">{{ dep.blood_type || 'Pendiente' }}</div>
                </div>
                <div class="bg-teal-50/70 border border-teal-200/80 p-2 rounded-xl">
                  <div class="text-3xs text-teal-800 font-bold">📏 Estatura / Talla</div>
                  <div class="font-black text-slate-800 mt-0.5">
                    {{ dep.height_cm ? `${dep.height_cm} cm` : 'Pendiente' }}
                  </div>
                </div>
              </div>

              <div v-if="dep.allergies" class="text-2xs p-2 rounded-lg bg-red-50 text-red-900 border border-red-200/70">
                <strong>⚠️ Alergias:</strong> {{ dep.allergies }}
              </div>

              <div v-if="dep.chronic_conditions" class="text-2xs p-2 rounded-lg bg-slate-100 text-slate-700">
                <strong>📋 Antecedentes:</strong> {{ dep.chronic_conditions }}
              </div>

              <div v-if="dep.notes" class="text-2xs italic text-slate-500 px-1 line-clamp-2">
                "{{ dep.notes }}"
              </div>
            </div>
          </div>

          <!-- Acciones en el Pie de la Tarjeta -->
          <div class="p-4 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between gap-2">
            <q-btn
              flat
              dense
              no-caps
              size="sm"
              color="teal-8"
              icon="edit"
              label="Editar Ficha"
              class="font-semibold text-xs"
              @click="openEditModal(dep)"
            />
            <q-btn
              unelevated
              size="sm"
              color="primary"
              icon="event_available"
              label="Agendar Cita"
              no-caps
              class="font-bold text-xs shadow-xs px-3 py-1.5"
              @click="bookAppointmentFor(dep)"
            />
          </div>
        </div>
      </div>

      <!-- 4. MODAL: Agregar / Editar Familiar -->
      <q-dialog v-model="showModal" persistent>
        <q-card class="rounded-2xl max-w-lg w-full p-2">
          <q-card-section class="flex items-center justify-between pb-2 border-b border-slate-100">
            <div class="flex items-center space-x-2">
              <div class="w-8 h-8 rounded-lg bg-teal-50 text-teal-800 flex items-center justify-center font-bold">
                <q-icon :name="isEditing ? 'edit' : 'person_add'" size="20px" color="teal" />
              </div>
              <h2 class="text-sm font-bold text-slate-900 m-0">
                {{ isEditing ? 'Editar Ficha del Familiar' : 'Registrar Nuevo Familiar' }}
              </h2>
            </div>
            <q-btn flat round dense icon="close" v-close-popup />
          </q-card-section>

          <q-card-section class="space-y-4 max-h-[75vh] overflow-y-auto pt-4">
            <!-- Si estamos editando, mostrar subida de fotografía del familiar -->
            <div v-if="isEditing" class="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center gap-4">
              <div class="w-14 h-14 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-lg overflow-hidden shrink-0 border border-white shadow-xs">
                <img
                  v-if="form.profile_picture_url"
                  :src="getResolvedAvatarUrl(form.profile_picture_url)"
                  class="w-full h-full object-cover"
                  alt="Foto"
                />
                <span v-else>{{ getInitials(form.full_name) }}</span>
              </div>
              <div class="flex-1 space-y-1">
                <div class="text-xs font-bold text-slate-800">Fotografía del Familiar</div>
                <div class="flex items-center gap-2">
                  <input
                    ref="avatarInputRef"
                    type="file"
                    accept="image/png, image/jpeg, image/webp"
                    class="hidden"
                    @change="handleAvatarFileSelect"
                  />
                  <q-btn
                    unelevated
                    dense
                    size="xs"
                    color="teal-8"
                    icon="photo_camera"
                    label="Subir Foto"
                    :loading="uploadingAvatar"
                    no-caps
                    class="px-2 py-1 font-semibold"
                    @click="triggerAvatarUpload"
                  />
                  <span class="text-3xs text-slate-400">JPG, PNG o WEBP (máx. 5MB)</span>
                </div>
              </div>
            </div>

            <!-- Datos Personales -->
            <div class="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-1 flex items-center">
              <q-icon name="badge" size="14px" class="mr-1 text-teal-600" />
              1. Datos de Identidad
            </div>

            <div class="space-y-3">
              <q-input
                v-model="form.full_name"
                outlined
                dense
                label="Nombre y Apellido del Familiar *"
                placeholder="Ej. Sofía Pérez"
                :rules="[val => !!val || 'El nombre es obligatorio']"
              />

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <q-select
                  v-model="form.relationship"
                  outlined
                  dense
                  :options="relationshipOptions"
                  emit-value
                  map-options
                  label="Parentesco o Relación *"
                  :rules="[val => !!val || 'El parentesco es obligatorio']"
                />

                <q-input
                  v-model="form.birth_date"
                  outlined
                  dense
                  type="date"
                  label="Fecha de Nacimiento *"
                  :rules="[val => !!val || 'La fecha es obligatoria']"
                />
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <q-select
                  v-model="form.gender"
                  outlined
                  dense
                  :options="['Femenino', 'Masculino', 'Otro']"
                  label="Sexo Biológico"
                />

                <q-input
                  v-model="form.id_document"
                  outlined
                  dense
                  label="Documento de Identidad / Cédula"
                  placeholder="Ej. V-32111222"
                />
              </div>

              <q-input
                v-model="form.phone"
                outlined
                dense
                label="Teléfono del Familiar (opcional)"
                placeholder="Ej. +58 412 1234567"
              />
            </div>

            <!-- Ficha Clínica Basal Permanente -->
            <div class="text-xs font-bold uppercase tracking-wider text-teal-800 border-b border-teal-100 pb-1 pt-2 flex items-center">
              <q-icon name="monitor_heart" size="14px" class="mr-1 text-teal-600" />
              2. Ficha Clínica Permanente del Familiar
            </div>

            <div class="space-y-3">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <q-select
                  v-model="form.blood_type"
                  outlined
                  dense
                  :options="['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'No lo sé']"
                  label="Grupo Sanguíneo"
                >
                  <template #prepend>
                    <q-icon name="bloodtype" color="red-6" size="18px" />
                  </template>
                </q-select>

                <q-input
                  v-model.number="form.height_cm"
                  outlined
                  dense
                  type="number"
                  label="Estatura / Talla (cm)"
                  placeholder="Ej. 130"
                  suffix="cm"
                  :rules="[val => !val || (val >= 20 && val <= 250) || 'Talla debe ser entre 20 y 250 cm']"
                />
              </div>

              <q-input
                v-model="form.allergies"
                outlined
                dense
                label="Alergias Conocidas"
                placeholder="Ej. Amoxicilina, Maní, Ninguna"
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="teal"
                    label="Ninguna"
                    class="text-2xs font-bold"
                    @click="form.allergies = 'Ninguna conocida'"
                  />
                </template>
              </q-input>

              <q-input
                v-model="form.chronic_conditions"
                outlined
                dense
                label="Antecedentes Médicos / Enfermedades"
                placeholder="Ej. Asma, Dermatitis, Ninguna"
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="teal"
                    label="Sin antecedentes"
                    class="text-2xs font-bold"
                    @click="form.chronic_conditions = 'Sin antecedentes patológicos'"
                  />
                </template>
              </q-input>

              <q-input
                v-model="form.notes"
                outlined
                dense
                type="textarea"
                rows="2"
                label="Notas Clínicas / Observaciones Especiales"
                placeholder="Observaciones para el médico especialista durante su consulta..."
              />
            </div>
          </q-card-section>

          <q-card-actions align="right" class="p-3 bg-slate-50 border-t border-slate-100">
            <q-btn flat label="Cancelar" color="slate-7" no-caps v-close-popup />
            <q-btn
              unelevated
              color="primary"
              :label="isEditing ? 'Guardar Cambios' : 'Registrar Familiar'"
              :loading="saving"
              no-caps
              class="font-bold text-xs px-4 py-2 shadow-xs"
              @click="submitForm"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- 5. Diálogo de Confirmación de Eliminación -->
      <q-dialog v-model="showDeleteDialog">
        <q-card class="rounded-2xl max-w-sm w-full p-4">
          <q-card-section class="text-center space-y-2">
            <div class="w-12 h-12 rounded-full bg-red-100 text-red-700 flex items-center justify-center mx-auto">
              <q-icon name="warning" size="24px" />
            </div>
            <h2 class="text-base font-bold text-slate-900 m-0">¿Eliminar a {{ selectedDependent?.full_name }}?</h2>
            <p class="text-xs text-slate-500 leading-relaxed">
              Esta acción desvinculará a este familiar de tu cuenta de paciente. Sus citas y consultas previas permanecerán en el archivo de la clínica.
            </p>
          </q-card-section>
          <q-card-actions align="center" class="gap-2 pt-2">
            <q-btn flat label="Cancelar" color="slate-7" no-caps v-close-popup />
            <q-btn
              unelevated
              color="negative"
              label="Sí, Eliminar"
              :loading="deleting"
              no-caps
              class="font-bold text-xs"
              @click="executeDelete"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>
    </div>
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from 'boot/axios'
import { Notify } from 'quasar'

const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)
const uploadingAvatar = ref(false)
const avatarInputRef = ref(null)

const dependents = ref([])
const showModal = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

const showDeleteDialog = ref(false)
const selectedDependent = ref(null)

const relationshipOptions = [
  { label: 'Hijo / Hija', value: 'HIJO' },
  { label: 'Cónyuge / Pareja', value: 'CONYUGE' },
  { label: 'Madre / Padre', value: 'PADRE' },
  { label: 'Hermano / Hermana', value: 'HERMANO' },
  { label: 'Otro Familiar / Tutor', value: 'OTRO' }
]

const form = reactive({
  full_name: '',
  relationship: 'HIJO',
  birth_date: '',
  gender: 'Femenino',
  id_document: '',
  phone: '',
  blood_type: 'O+',
  height_cm: null,
  allergies: '',
  chronic_conditions: '',
  notes: '',
  profile_picture_url: null
})

function getInitials (name) {
  if (!name) return 'F'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

function getResolvedAvatarUrl (url) {
  if (!url) return null
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  const apiBase = process.env.CLIENT_API_URL || process.env.API_URL || process.env.VITE_API_URL || ''
  if (apiBase) {
    return `${apiBase.replace(/\/$/, '')}${url.startsWith('/') ? '' : '/'}${url}`
  }
  return url
}

function formatRelationship (rel) {
  const map = {
    HIJO: 'Hijo(a)',
    CONYUGE: 'Cónyuge',
    PADRE: 'Padre/Madre',
    HERMANO: 'Hermano(a)',
    OTRO: 'Familiar'
  }
  return map[rel] || rel
}

function getRelationshipBadgeClass (rel) {
  switch (rel) {
    case 'HIJO':
      return 'bg-blue-100 text-blue-800'
    case 'CONYUGE':
      return 'bg-rose-100 text-rose-800'
    case 'PADRE':
      return 'bg-purple-100 text-purple-800'
    case 'HERMANO':
      return 'bg-amber-100 text-amber-800'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}

async function loadDependents () {
  loading.value = true
  try {
    const { data } = await api.get('/patients/me/dependents')
    dependents.value = data || []
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al consultar familiares.'
    })
  } finally {
    loading.value = false
  }
}

function resetForm () {
  form.full_name = ''
  form.relationship = 'HIJO'
  form.birth_date = ''
  form.gender = 'Femenino'
  form.id_document = ''
  form.phone = ''
  form.blood_type = 'O+'
  form.height_cm = null
  form.allergies = ''
  form.chronic_conditions = ''
  form.notes = ''
  form.profile_picture_url = null
}

function openCreateModal () {
  isEditing.value = false
  editingId.value = null
  resetForm()
  showModal.value = true
}

function openEditModal (dep) {
  isEditing.value = true
  editingId.value = dep.id
  form.full_name = dep.full_name || ''
  form.relationship = dep.relationship || 'HIJO'
  form.birth_date = dep.birth_date || ''
  form.gender = dep.gender || 'Femenino'
  form.id_document = dep.id_document || ''
  form.phone = dep.phone || ''
  form.blood_type = dep.blood_type || 'O+'
  form.height_cm = dep.height_cm != null ? Number(dep.height_cm) : null
  form.allergies = dep.allergies || ''
  form.chronic_conditions = dep.chronic_conditions || ''
  form.notes = dep.notes || ''
  form.profile_picture_url = dep.profile_picture_url || null
  showModal.value = true
}

async function submitForm () {
  if (!form.full_name || !form.birth_date) {
    Notify.create({
      type: 'warning',
      message: 'Por favor completa el nombre y la fecha de nacimiento.'
    })
    return
  }

  saving.value = true
  try {
    const payload = {
      full_name: form.full_name.trim(),
      relationship: form.relationship,
      birth_date: form.birth_date,
      gender: form.gender,
      id_document: form.id_document?.trim() || undefined,
      phone: form.phone?.trim() || undefined,
      blood_type: form.blood_type || undefined,
      height_cm: form.height_cm != null ? Number(form.height_cm) : undefined,
      allergies: form.allergies?.trim() || undefined,
      chronic_conditions: form.chronic_conditions?.trim() || undefined,
      notes: form.notes?.trim() || undefined
    }

    if (isEditing.value && editingId.value) {
      await api.put(`/patients/me/dependents/${editingId.value}`, payload)
      Notify.create({ type: 'positive', message: '¡Ficha del familiar actualizada exitosamente!' })
    } else {
      await api.post('/patients/me/dependents', payload)
      Notify.create({ type: 'positive', message: '¡Familiar registrado con éxito!' })
    }
    showModal.value = false
    await loadDependents()
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al guardar el familiar.'
    })
  } finally {
    saving.value = false
  }
}

function triggerAvatarUpload () {
  if (avatarInputRef.value) {
    avatarInputRef.value.click()
  }
}

async function handleAvatarFileSelect (event) {
  const file = event.target.files?.[0]
  if (!file || !editingId.value) return

  if (file.size > 5 * 1024 * 1024) {
    Notify.create({ type: 'negative', message: 'La imagen excede el límite permitido de 5 MB.' })
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  uploadingAvatar.value = true
  try {
    const { data } = await api.post(`/patients/me/dependents/${editingId.value}/avatar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    form.profile_picture_url = `${data.profile_picture_url}?t=${Date.now()}`
    Notify.create({ type: 'positive', message: 'Fotografía del familiar actualizada.' })
    await loadDependents()
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al subir la fotografía.'
    })
  } finally {
    uploadingAvatar.value = false
    if (event.target) {
      event.target.value = ''
    }
  }
}

function confirmDelete (dep) {
  selectedDependent.value = dep
  showDeleteDialog.value = true
}

async function executeDelete () {
  if (!selectedDependent.value) return
  deleting.value = true
  try {
    await api.delete(`/patients/me/dependents/${selectedDependent.value.id}`)
    Notify.create({ type: 'positive', message: 'Familiar eliminado del registro.' })
    showDeleteDialog.value = false
    await loadDependents()
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al eliminar el familiar.'
    })
  } finally {
    deleting.value = false
  }
}

function bookAppointmentFor (dep) {
  router.push({
    path: '/appointments/book',
    query: {
      dependent_id: dep.id,
      beneficiary: 'dependent'
    }
  })
}

onMounted(() => {
  loadDependents()
})
</script>
