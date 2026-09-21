<template>
  <q-page class="p-4 sm:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-4xl mx-auto space-y-6">
      <!-- 1. Encabezado del Perfil -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center space-x-3.5">
          <div class="w-12 h-12 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-xl shadow-sm">
            <q-icon name="person" size="28px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900 leading-tight">Mi Perfil de Salud & Ficha Médica</h1>
            <p class="text-xs text-slate-500 mt-0.5">
              Gestiona tus datos personales, ficha clínica permanente y contacto de emergencia.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2 self-end sm:self-center">
          <q-btn
            outline
            color="teal-8"
            icon="family_restroom"
            label="Mis Familiares"
            to="/patient/family"
            no-caps
            class="text-xs font-bold px-3 py-2"
          />
          <q-btn
            unelevated
            color="primary"
            icon="save"
            label="Guardar Perfil"
            :loading="saving"
            no-caps
            class="text-xs font-bold shadow-sm px-4 py-2"
            @click="saveProfile"
          />
        </div>
      </div>

      <!-- Estado de carga -->
      <div v-if="loading" class="text-center py-16">
        <q-spinner-dots color="teal" size="48px" />
        <p class="text-xs text-slate-500 mt-2">Cargando tu información médica...</p>
      </div>

      <div v-else class="space-y-6">
        <!-- 2. Tarjeta de Resumen y Fotografía de Perfil -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div class="flex flex-col sm:flex-row items-center gap-6">
            <!-- Avatar con botón de subida -->
            <div class="relative group shrink-0">
              <div class="w-24 h-24 rounded-2xl bg-gradient-to-tr from-teal-700 to-teal-500 text-white flex items-center justify-center font-bold text-2xl shadow-md overflow-hidden border-2 border-white ring-2 ring-teal-100">
                <img
                  v-if="profile.profile_picture_url"
                  :src="getResolvedAvatarUrl(profile.profile_picture_url)"
                  class="w-full h-full object-cover"
                  alt="Foto del paciente"
                />
                <span v-else class="text-3xl">{{ getInitials(profile.full_name || profile.email) }}</span>
              </div>
              <div v-if="uploadingAvatar" class="absolute inset-0 bg-black/50 rounded-2xl flex items-center justify-center">
                <q-spinner color="white" size="24px" />
              </div>
            </div>

            <!-- Información General y Completitud -->
            <div class="flex-1 text-center sm:text-left space-y-2">
              <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                <h2 class="text-lg font-black text-slate-800 m-0">
                  {{ profile.full_name || 'Paciente VitaRecord' }}
                </h2>
                <!-- Badge de completitud clínica -->
                <span
                  v-if="profile.is_profile_complete"
                  class="inline-flex items-center text-2xs px-2.5 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 w-fit self-center sm:self-auto"
                >
                  <q-icon name="check_circle" size="13px" class="mr-1 text-emerald-600" />
                  Ficha Clínica Completa
                </span>
                <span
                  v-else
                  class="inline-flex items-center text-2xs px-2.5 py-0.5 rounded-full font-bold bg-amber-100 text-amber-900 border border-amber-300 w-fit self-center sm:self-auto"
                >
                  <q-icon name="warning_amber" size="13px" class="mr-1 text-amber-700" />
                  Ficha Clínica Incompleta
                </span>
              </div>

              <div class="text-xs text-slate-500 flex flex-wrap items-center justify-center sm:justify-start gap-3">
                <span class="flex items-center">
                  <q-icon name="mail" size="14px" class="mr-1 text-slate-400" />
                  {{ profile.email }}
                </span>
                <span v-if="profile.identification_number" class="flex items-center">
                  <q-icon name="badge" size="14px" class="mr-1 text-slate-400" />
                  {{ profile.identification_number }}
                </span>
                <span v-if="profile.phone" class="flex items-center">
                  <q-icon name="phone" size="14px" class="mr-1 text-slate-400" />
                  {{ profile.phone }}
                </span>
              </div>

              <div class="pt-2 flex flex-wrap items-center justify-center sm:justify-start gap-2">
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
                  size="sm"
                  color="teal-8"
                  icon="photo_camera"
                  label="Subir Fotografía"
                  :loading="uploadingAvatar"
                  no-caps
                  class="px-3 py-1 font-semibold"
                  @click="triggerAvatarUpload"
                />
                <span class="text-2xs text-slate-400">
                  Formatos admitidos: JPG, PNG o WEBP (Máx. 5MB)
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Acceso a Mi Núcleo Familiar -->
        <div class="bg-gradient-to-r from-teal-50 to-emerald-50 border border-teal-200 p-5 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs">
          <div class="flex items-center space-x-3.5">
            <div class="w-11 h-11 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-lg shadow-xs shrink-0">
              <q-icon name="family_restroom" size="24px" />
            </div>
            <div>
              <h3 class="text-sm font-bold text-slate-900 leading-tight">¿Tienes familiares o personas a tu cargo?</h3>
              <p class="text-xs text-slate-600 mt-0.5 leading-relaxed">
                Gestiona a tus dependientes (hijos, cónyuge, padres). Podrás subir sus fotografías individuales y registrar sus fichas médicas permanentes para que sus citas se agenden sin repetir datos.
              </p>
            </div>
          </div>
          <q-btn
            unelevated
            color="teal-8"
            icon="people"
            label="Gestionar Familiares"
            to="/patient/family"
            no-caps
            class="text-xs font-bold px-4 py-2 shrink-0 self-stretch sm:self-center"
          />
        </div>

        <!-- 3. SECCIÓN: Ficha Clínica Basal (Datos Inmutables en el Tiempo) -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border-2 border-teal-500/60 space-y-4">
          <div class="flex items-center justify-between border-b border-teal-100 pb-2.5">
            <div class="flex items-center space-x-2">
              <div class="w-8 h-8 rounded-lg bg-teal-50 text-teal-800 flex items-center justify-center font-bold">
                <q-icon name="monitor_heart" size="20px" color="teal" />
              </div>
              <div>
                <h3 class="text-sm font-black text-slate-900 uppercase tracking-wider">
                  Ficha Clínica Basal (Datos Permanentes)
                </h3>
                <p class="text-2xs text-slate-500">
                  Estos datos no cambian con frecuencia y no tendrás que volver a llenarlos en cada cita.
                </p>
              </div>
            </div>
            <span class="hidden sm:inline-block text-2xs px-2 py-0.5 rounded bg-teal-50 text-teal-800 font-bold border border-teal-200">
              Auto-vinculado a tus Citas
            </span>
          </div>

          <div class="p-3.5 bg-teal-50/70 border border-teal-200 rounded-xl flex items-start gap-2.5 text-xs text-teal-900 leading-relaxed">
            <q-icon name="info" color="teal" size="18px" class="mt-0.5 shrink-0" />
            <div>
              <strong>Importante para tu atención médica:</strong>
              Al mantener tu grupo sanguíneo y estatura registrados, el sistema calculará de forma automática tu IMC y compartirá tus antecedentes relevantes con tu especialista en cada consulta sin pedirte la misma información repetidamente.
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
            <!-- Grupo Sanguíneo -->
            <div>
              <q-select
                v-model="profile.blood_type"
                outlined
                dense
                :options="['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']"
                label="Grupo Sanguíneo *"
                bg-color="white"
                hint="Ej. O+, A+, etc."
              >
                <template #prepend>
                  <q-icon name="bloodtype" color="red-6" />
                </template>
              </q-select>
            </div>

            <!-- Estatura en cm -->
            <div>
              <q-input
                v-model.number="profile.height_cm"
                outlined
                dense
                type="number"
                label="Estatura / Talla (cm) *"
                placeholder="Ej. 165"
                suffix="cm"
                bg-color="white"
                hint="Tu estatura como adulto no cambia en el tiempo"
                :rules="[val => !val || (val >= 40 && val <= 250) || 'Talla debe ser entre 40 y 250 cm']"
              >
                <template #prepend>
                  <q-icon name="height" color="teal" />
                </template>
              </q-input>
            </div>
          </div>

          <!-- Alergias y Enfermedades Crónicas -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <q-input
                v-model="profile.allergies"
                outlined
                dense
                label="Alergias Conocidas a Medicamentos / Sustancias"
                placeholder="Ej. Penicilina, Sulfas, AINEs"
                bg-color="white"
                autogrow
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="teal"
                    label="Ninguna"
                    class="text-2xs font-bold"
                    @click="profile.allergies = 'Ninguna conocida'"
                  />
                </template>
              </q-input>
            </div>

            <div>
              <q-input
                v-model="profile.chronic_conditions"
                outlined
                dense
                label="Enfermedades Crónicas / Antecedentes Patológicos"
                placeholder="Ej. Hipertensión, Diabetes, Asma"
                bg-color="white"
                autogrow
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="teal"
                    label="Sin antecedentes"
                    class="text-2xs font-bold"
                    @click="profile.chronic_conditions = 'Sin antecedentes patológicos'"
                  />
                </template>
              </q-input>
            </div>
          </div>
        </div>

        <!-- 4. SECCIÓN: Datos Personales y Demográficos -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
          <div class="flex items-center space-x-2 border-b border-slate-100 pb-2.5">
            <div class="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center font-bold">
              <q-icon name="badge" size="20px" />
            </div>
            <div>
              <h3 class="text-sm font-black text-slate-900 uppercase tracking-wider">
                Datos Personales & Identificación
              </h3>
              <p class="text-2xs text-slate-500">
                Información oficial del paciente para expedientes y emisión de recetas.
              </p>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <q-input
              v-model="profile.full_name"
              outlined
              dense
              label="Nombre y Apellido *"
              placeholder="Ej. María Hernández"
              :rules="[val => !!val || 'El nombre es obligatorio']"
            />

            <q-input
              v-model="profile.identification_number"
              outlined
              dense
              label="Cédula / Documento de Identidad *"
              placeholder="Ej. V-18765432"
              :rules="[val => !!val || 'El documento es obligatorio']"
            />

            <q-input
              v-model="profile.phone"
              outlined
              dense
              label="Teléfono Móvil (WhatsApp) *"
              placeholder="Ej. +58 412 1234567"
              :rules="[val => !!val || 'El teléfono es obligatorio']"
            />

            <q-input
              v-model="profile.birth_date_str"
              outlined
              dense
              type="date"
              label="Fecha de Nacimiento"
            />

            <q-select
              v-model="profile.gender"
              outlined
              dense
              :options="['Femenino', 'Masculino', 'Otro']"
              label="Sexo Biológico"
            />

            <q-input
              v-model="profile.country"
              outlined
              dense
              label="País"
              placeholder="Venezuela"
            />

            <q-input
              v-model="profile.city"
              outlined
              dense
              label="Ciudad / Estado"
              placeholder="Ej. Caracas, Miranda"
            />

            <div class="sm:col-span-2">
              <q-input
                v-model="profile.address"
                outlined
                dense
                label="Dirección de Habitación"
                placeholder="Calle, Edificio / Casa, Apto"
              />
            </div>
          </div>
        </div>

        <!-- 5. SECCIÓN: Contacto de Emergencia -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
          <div class="flex items-center space-x-2 border-b border-slate-100 pb-2.5">
            <div class="w-8 h-8 rounded-lg bg-red-50 text-red-700 flex items-center justify-center font-bold">
              <q-icon name="emergency" size="20px" color="red-7" />
            </div>
            <div>
              <h3 class="text-sm font-black text-slate-900 uppercase tracking-wider">
                Contacto de Emergencia
              </h3>
              <p class="text-2xs text-slate-500">
                Persona de contacto en caso de imprevistos durante tu consulta médica.
              </p>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <q-input
              v-model="profile.emergency_contact_name"
              outlined
              dense
              label="Nombre y Apellido del Contacto"
              placeholder="Ej. Carlos Pérez"
            >
              <template #prepend>
                <q-icon name="person_outline" size="18px" />
              </template>
            </q-input>

            <q-input
              v-model="profile.emergency_contact_phone"
              outlined
              dense
              label="Teléfono de Emergencia"
              placeholder="Ej. +58 414 7654321"
            >
              <template #prepend>
                <q-icon name="phone" size="18px" />
              </template>
            </q-input>

            <q-select
              v-model="profile.emergency_contact_relationship"
              outlined
              dense
              :options="['Cónyuge / Pareja', 'Madre / Padre', 'Hijo / Hija', 'Hermano / Hermana', 'Familiar', 'Amigo / Tutor', 'Otro']"
              label="Parentesco o Relación"
            />
          </div>
        </div>

        <!-- Botón Inferior de Guardado -->
        <div class="flex justify-end p-2">
          <q-btn
            unelevated
            color="primary"
            icon="save"
            label="Guardar Todos los Cambios"
            :loading="saving"
            no-caps
            class="text-sm font-bold shadow-md px-6 py-2.5 rounded-xl"
            @click="saveProfile"
          />
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from 'boot/axios'
import { Notify } from 'quasar'

const loading = ref(true)
const saving = ref(false)
const uploadingAvatar = ref(false)
const avatarInputRef = ref(null)

const profile = reactive({
  id: '',
  email: '',
  full_name: '',
  phone: '',
  identification_number: '',
  birth_date_str: '',
  gender: '',
  address: '',
  city: '',
  country: 'Venezuela',
  blood_type: null,
  height_cm: null,
  allergies: '',
  chronic_conditions: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  emergency_contact_relationship: '',
  profile_picture_url: null,
  is_profile_complete: false
})

function getInitials (nameOrEmail) {
  if (!nameOrEmail) return 'P'
  const parts = nameOrEmail.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return nameOrEmail.substring(0, 2).toUpperCase()
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

async function loadProfile () {
  loading.value = true
  try {
    const { data } = await api.get('/patients/me/profile')
    profile.id = data.id
    profile.email = data.email
    profile.full_name = data.full_name || ''
    profile.phone = data.phone || ''
    profile.identification_number = data.identification_number || ''
    profile.gender = data.gender || ''
    profile.address = data.address || ''
    profile.city = data.city || ''
    profile.country = data.country || 'Venezuela'
    profile.blood_type = data.blood_type || null
    profile.height_cm = data.height_cm != null ? Number(data.height_cm) : null
    profile.allergies = data.allergies || ''
    profile.chronic_conditions = data.chronic_conditions || ''
    profile.emergency_contact_name = data.emergency_contact_name || ''
    profile.emergency_contact_phone = data.emergency_contact_phone || ''
    profile.emergency_contact_relationship = data.emergency_contact_relationship || ''
    profile.profile_picture_url = data.profile_picture_url || null
    profile.is_profile_complete = !!data.is_profile_complete

    if (data.birth_date) {
      profile.birth_date_str = typeof data.birth_date === 'string' ? data.birth_date.substring(0, 10) : ''
    } else {
      profile.birth_date_str = ''
    }
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al cargar tu perfil de paciente.'
    })
  } finally {
    loading.value = false
  }
}

async function saveProfile () {
  saving.value = true
  try {
    const payload = {
      full_name: profile.full_name || undefined,
      phone: profile.phone || undefined,
      identification_number: profile.identification_number || undefined,
      birth_date: profile.birth_date_str || undefined,
      gender: profile.gender || undefined,
      address: profile.address || undefined,
      city: profile.city || undefined,
      country: profile.country || 'Venezuela',
      blood_type: profile.blood_type || undefined,
      height_cm: profile.height_cm != null ? Number(profile.height_cm) : undefined,
      allergies: profile.allergies || undefined,
      chronic_conditions: profile.chronic_conditions || undefined,
      emergency_contact_name: profile.emergency_contact_name || undefined,
      emergency_contact_phone: profile.emergency_contact_phone || undefined,
      emergency_contact_relationship: profile.emergency_contact_relationship || undefined
    }

    const { data } = await api.put('/patients/me/profile', payload)
    profile.is_profile_complete = !!data.is_profile_complete

    Notify.create({
      type: 'positive',
      message: '¡Perfil médico actualizado exitosamente!'
    })
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al guardar los cambios en el perfil.'
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
  if (!file) return

  if (file.size > 5 * 1024 * 1024) {
    Notify.create({
      type: 'negative',
      message: 'La imagen excede el límite permitido de 5 MB.'
    })
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  uploadingAvatar.value = true
  try {
    const { data } = await api.post('/patients/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    profile.profile_picture_url = `${data.profile_picture_url}?t=${Date.now()}`
    Notify.create({
      type: 'positive',
      message: 'Fotografía de perfil actualizada con éxito.'
    })
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al subir la fotografía de perfil.'
    })
  } finally {
    uploadingAvatar.value = false
    if (event.target) {
      event.target.value = ''
    }
  }
}

onMounted(() => {
  loadProfile()
})
</script>
