<template>
  <q-page class="p-6 bg-slate-50 min-h-screen">
    <div class="max-w-6xl mx-auto space-y-6">
      <!-- Header -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center space-x-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
              SaaS Master • SuperAdmin
            </span>
            <span class="text-xs text-slate-400">Multi-Tenancy y Aislamiento</span>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 mt-1">Gestión de Clínicas y Tenants</h1>
          <p class="text-sm text-slate-500 mt-0.5">
            Aprovisionamiento, activación, edición y baja definitiva de sedes clínicas en la plataforma VitaRecord.
          </p>
        </div>

        <div class="flex items-center space-x-3">
          <q-btn
            color="primary"
            icon="add"
            label="Nueva Clínica / Tenant"
            no-caps
            class="font-semibold shadow-sm"
            @click="openCreateModal"
          />
        </div>
      </div>

      <!-- Lista de Clínicas -->
      <div class="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden">
        <div v-if="loading" class="text-center py-16">
          <q-spinner-dots color="primary" size="48px" />
          <p class="text-slate-500 mt-3 text-sm">Consultando clínicas registradas...</p>
        </div>

        <div v-else-if="clinics.length === 0" class="text-center py-16 px-4">
          <div class="w-16 h-16 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
            <q-icon name="apartment" size="36px" />
          </div>
          <h3 class="text-lg font-semibold text-slate-800">No hay clínicas configuradas</h3>
          <p class="text-slate-500 text-sm mt-1">Crea el primer tenant para comenzar a operar.</p>
        </div>

        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="clinic in clinics"
            :key="clinic.id"
            class="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/80 transition-colors"
          >
            <div class="flex items-start space-x-4">
              <div
                class="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg"
                :class="clinic.is_active ? 'bg-teal-100 text-teal-700' : 'bg-slate-100 text-slate-400'"
              >
                <q-icon name="apartment" size="24px" />
              </div>

              <div class="space-y-1">
                <div class="flex items-center space-x-2">
                  <h3 class="font-bold text-slate-900 text-base">{{ clinic.name }}</h3>
                  <span
                    class="px-2 py-0.5 rounded-full text-xs font-semibold"
                    :class="clinic.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'"
                  >
                    {{ clinic.is_active ? 'Activa' : 'Inactiva / Suspendida' }}
                  </span>
                </div>

                <div class="text-xs text-slate-500 flex flex-wrap gap-x-4 gap-y-1">
                  <span><strong>ID:</strong> <code class="font-mono">{{ clinic.id }}</code></span>
                  <span><strong>Slug:</strong> {{ clinic.slug }}</span>
                  <span><strong>Zona Horaria:</strong> {{ clinic.timezone }}</span>
                  <span><strong>País:</strong> {{ clinic.country_code }}</span>
                </div>

                <div class="text-xs text-slate-600 flex flex-wrap gap-x-4 gap-y-1 pt-0.5">
                  <span v-if="clinic.phone" class="flex items-center space-x-1 text-slate-700">
                    <q-icon name="phone" size="14px" class="text-slate-400" />
                    <span><strong>Tel:</strong> {{ clinic.phone }}</span>
                  </span>
                  <span v-else class="text-slate-400 italic">Sin teléfono registrado</span>

                  <span v-if="clinic.address" class="flex items-center space-x-1 text-slate-700">
                    <q-icon name="location_on" size="14px" class="text-slate-400" />
                    <span><strong>Dirección:</strong> {{ clinic.address }}</span>
                  </span>
                  <span v-else class="text-slate-400 italic">Sin dirección registrada</span>
                </div>
              </div>
            </div>

            <!-- Acciones -->
            <div class="flex items-center space-x-2 self-end md:self-center">
              <!-- Botón Editar -->
              <q-btn
                flat
                round
                dense
                color="primary"
                icon="edit"
                @click="openEditModal(clinic)"
              >
                <q-tooltip>Editar datos de la clínica</q-tooltip>
              </q-btn>

              <!-- Botón Inactivar / Activar -->
              <q-btn
                flat
                round
                dense
                :color="clinic.is_active ? 'amber-9' : 'positive'"
                :icon="clinic.is_active ? 'block' : 'check_circle'"
                @click="confirmToggleActive(clinic)"
              >
                <q-tooltip>
                  {{ clinic.is_active ? 'Inactivar sede y suspender accesos' : 'Activar sede y restaurar accesos' }}
                </q-tooltip>
              </q-btn>

              <!-- Botón Eliminar -->
              <q-btn
                flat
                round
                dense
                color="negative"
                icon="delete"
                @click="confirmDelete(clinic)"
              >
                <q-tooltip>Eliminar sede y recursos asociados</q-tooltip>
              </q-btn>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Crear Nueva Clínica -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 460px; max-width: 520px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-teal-800 to-indigo-900 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="domain_add" size="24px" />
            <h3 class="text-lg font-bold">Dar de Alta Nuevo Tenant</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6">
          <form class="space-y-4" @submit.prevent="submitCreateClinic">
            <q-input
              v-model="formName"
              label="Nombre de la Clínica (ej. Clínica VitaRecord Norte)"
              filled
              required
              @update:model-value="autoGenerateSlug"
            />
            <q-input
              v-model="formSlug"
              label="Slug único de acceso (ej. vitarecord-norte)"
              filled
              hint="Se usará como subdominio o identificador único de tenant"
              required
            />
            <div class="grid grid-cols-2 gap-3">
              <q-input
                v-model="formTimezone"
                label="Zona Horaria (ej. America/Caracas)"
                filled
                required
              />
              <q-input
                v-model="formCountry"
                label="País (ISO ej. VE)"
                filled
                maxlength="2"
                required
              />
            </div>
            <q-input
              v-model="formPhone"
              label="Teléfono de Contacto (ej. +58 412 1234567)"
              filled
              hint="Se informará a los pacientes para contacto directo"
            />
            <q-input
              v-model="formAddress"
              label="Dirección Física (ej. Av. Principal Torre Médica Piso 4)"
              filled
            />

            <div v-if="createError" class="p-3 rounded-lg bg-red-50 text-red-700 text-xs flex items-center">
              <q-icon name="warning" class="mr-2" size="16px" />
              <span>{{ createError }}</span>
            </div>

            <div class="pt-3 flex justify-end space-x-3">
              <q-btn flat label="Cancelar" v-close-popup no-caps />
              <q-btn
                type="submit"
                color="primary"
                label="Crear Tenant"
                icon="check"
                no-caps
                class="font-semibold"
                :loading="submitting"
              />
            </div>
          </form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Modal Editar Clínica -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 460px; max-width: 520px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-teal-800 to-indigo-900 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="edit" size="24px" />
            <h3 class="text-lg font-bold">Editar Clínica / Tenant</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6">
          <form class="space-y-4" @submit.prevent="submitEditClinic">
            <q-input
              v-model="editForm.name"
              label="Nombre de la Clínica"
              filled
              required
            />
            <q-input
              v-model="editForm.slug"
              label="Slug único de acceso"
              filled
              required
            />
            <div class="grid grid-cols-2 gap-3">
              <q-input
                v-model="editForm.timezone"
                label="Zona Horaria"
                filled
                required
              />
              <q-input
                v-model="editForm.country_code"
                label="País (ISO)"
                filled
                maxlength="2"
                required
              />
            </div>
            <q-input
              v-model="editForm.phone"
              label="Teléfono de Contacto"
              filled
              hint="Número telefónico directo de la sede"
            />
            <q-input
              v-model="editForm.address"
              label="Dirección Física"
              filled
            />

            <div v-if="editError" class="p-3 rounded-lg bg-red-50 text-red-700 text-xs flex items-center">
              <q-icon name="warning" class="mr-2" size="16px" />
              <span>{{ editError }}</span>
            </div>

            <div class="pt-3 flex justify-end space-x-3">
              <q-btn flat label="Cancelar" v-close-popup no-caps />
              <q-btn
                type="submit"
                color="primary"
                label="Guardar Cambios"
                icon="save"
                no-caps
                class="font-semibold"
                :loading="editSubmitting"
              />
            </div>
          </form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Modal Confirmar Inactivar / Activar -->
    <q-dialog v-model="showToggleDialog">
      <q-card style="min-width: 400px; max-width: 480px; border-radius: 16px;">
        <q-card-section class="p-6 text-center">
          <div
            class="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
            :class="selectedClinic?.is_active ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'"
          >
            <q-icon :name="selectedClinic?.is_active ? 'block' : 'check_circle'" size="36px" />
          </div>

          <h3 class="text-lg font-bold text-slate-900">
            {{ selectedClinic?.is_active ? '¿Inactivar sede clínica?' : '¿Reactivar sede clínica?' }}
          </h3>

          <div v-if="selectedClinic?.is_active" class="mt-3 text-sm text-slate-600 space-y-2 text-left bg-amber-50/80 p-3.5 rounded-xl border border-amber-200/80">
            <p class="font-medium text-amber-900">Al inactivar <strong>{{ selectedClinic?.name }}</strong>:</p>
            <ul class="list-disc list-inside text-xs space-y-1 text-amber-800">
              <li>No será visible en directorios ni en agendamiento público.</li>
              <li>Los administradores de la clínica y secretarias quedarán <strong>suspendidos de inmediato</strong> sin acceso al sistema.</li>
              <li>Se cerrarán automáticamente todas sus sesiones activas.</li>
            </ul>
          </div>

          <div v-else class="mt-3 text-sm text-slate-600 space-y-2 text-left bg-emerald-50/80 p-3.5 rounded-xl border border-emerald-200/80">
            <p class="font-medium text-emerald-900">Al reactivar <strong>{{ selectedClinic?.name }}</strong>:</p>
            <ul class="list-disc list-inside text-xs space-y-1 text-emerald-800">
              <li>Volverá a estar disponible para agendamiento y visible en la plataforma.</li>
              <li>Los administradores y secretarias suspendidos recuperarán el acceso al sistema.</li>
            </ul>
          </div>

          <div class="mt-6 flex justify-end space-x-3">
            <q-btn flat label="Cancelar" v-close-popup no-caps />
            <q-btn
              :color="selectedClinic?.is_active ? 'amber-9' : 'positive'"
              :label="selectedClinic?.is_active ? 'Sí, Inactivar Tenant' : 'Sí, Reactivar Tenant'"
              no-caps
              class="font-semibold"
              :loading="toggleSubmitting"
              @click="executeToggleActive"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Modal Confirmar Eliminación Definitiva -->
    <q-dialog v-model="showDeleteDialog">
      <q-card style="min-width: 440px; max-width: 520px; border-radius: 16px;">
        <q-card-section class="p-6">
          <div class="w-16 h-16 rounded-full bg-red-100 text-red-700 flex items-center justify-center mx-auto mb-4">
            <q-icon name="warning" size="36px" />
          </div>

          <h3 class="text-xl font-bold text-center text-slate-900">
            ¿Eliminar permanentemente el Tenant?
          </h3>

          <p class="text-center text-sm text-slate-600 mt-1">
            Esta acción es <strong>irreversible</strong> y dará de baja a <strong>{{ selectedClinic?.name }}</strong>.
          </p>

          <div class="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 space-y-2">
            <p class="font-bold flex items-center">
              <q-icon name="notifications_active" class="mr-1.5" size="16px" />
              Notificación a Pacientes:
            </p>
            <p>
              Si existen citas activas o pendientes, el sistema enviará automáticamente un correo electrónico a cada paciente notificándole la cancelación e incluyendo el <strong>número telefónico</strong> y <strong>dirección</strong> de la clínica para que puedan coordinar directamente con el centro por otros medios.
            </p>
            <hr class="border-red-200" />
            <p class="font-bold">Efectos en cascada:</p>
            <ul class="list-disc list-inside space-y-0.5">
              <li>Se eliminarán los usuarios Administradores y Secretarias del tenant.</li>
              <li>Se desvinculará a los médicos afiliados.</li>
              <li>Se cancelarán y purgarán las citas, salas y registros vinculados a la sede.</li>
            </ul>
          </div>

          <div class="mt-6 flex justify-end space-x-3">
            <q-btn flat label="Cancelar" v-close-popup no-caps />
            <q-btn
              color="negative"
              label="Eliminar Tenant Definitivamente"
              icon="delete_forever"
              no-caps
              class="font-bold"
              :loading="deleteSubmitting"
              @click="executeDelete"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

const $q = useQuasar()
const clinics = ref([])
const loading = ref(false)

// Modales y estados
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showToggleDialog = ref(false)
const showDeleteDialog = ref(false)
const selectedClinic = ref(null)

// Formulario de creación
const formName = ref('')
const formSlug = ref('')
const formTimezone = ref('America/Caracas')
const formCountry = ref('VE')
const formPhone = ref('')
const formAddress = ref('')
const submitting = ref(false)
const createError = ref('')

// Formulario de edición
const editForm = reactive({
  id: '',
  name: '',
  slug: '',
  timezone: '',
  country_code: '',
  phone: '',
  address: ''
})
const editSubmitting = ref(false)
const editError = ref('')

// Acciones toggle y delete
const toggleSubmitting = ref(false)
const deleteSubmitting = ref(false)

function autoGenerateSlug (val) {
  if (!formSlug.value || formSlug.value === formName.value.toLowerCase().replace(/[^a-z0-9]/g, '-').slice(0, -1)) {
    formSlug.value = (val || '')
      .toLowerCase()
      .trim()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
  }
}

async function loadClinics () {
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.get('/clinics', {
      headers: { Authorization: `Bearer ${token}` }
    })
    clinics.value = data
  } catch (err) {
    console.error('Error al cargar clínicas:', err)
    $q.notify({
      type: 'negative',
      message: 'Error al consultar clínicas.',
      position: 'top'
    })
  } finally {
    loading.value = false
  }
}

function openCreateModal () {
  formName.value = ''
  formSlug.value = ''
  formTimezone.value = 'America/Caracas'
  formCountry.value = 'VE'
  formPhone.value = ''
  formAddress.value = ''
  createError.value = ''
  showCreateDialog.value = true
}

async function submitCreateClinic () {
  submitting.value = true
  createError.value = ''
  try {
    const token = localStorage.getItem('access_token')
    await api.post(
      '/clinics',
      {
        name: formName.value,
        slug: formSlug.value,
        timezone: formTimezone.value,
        country_code: formCountry.value.toUpperCase(),
        phone: formPhone.value || null,
        address: formAddress.value || null
      },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    showCreateDialog.value = false
    $q.notify({
      type: 'positive',
      message: 'Clínica / Tenant creado exitosamente.',
      position: 'top'
    })
    await loadClinics()
  } catch (err) {
    createError.value = err.response?.data?.detail || 'No se pudo crear la clínica.'
  } finally {
    submitting.value = false
  }
}

function openEditModal (clinic) {
  editForm.id = clinic.id
  editForm.name = clinic.name
  editForm.slug = clinic.slug
  editForm.timezone = clinic.timezone
  editForm.country_code = clinic.country_code
  editForm.phone = clinic.phone || ''
  editForm.address = clinic.address || ''
  editError.value = ''
  showEditDialog.value = true
}

async function submitEditClinic () {
  editSubmitting.value = true
  editError.value = ''
  try {
    const token = localStorage.getItem('access_token')
    await api.put(
      `/clinics/${editForm.id}`,
      {
        name: editForm.name,
        slug: editForm.slug,
        timezone: editForm.timezone,
        country_code: editForm.country_code.toUpperCase(),
        phone: editForm.phone || null,
        address: editForm.address || null
      },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    showEditDialog.value = false
    $q.notify({
      type: 'positive',
      message: 'Datos de la clínica actualizados correctamente.',
      position: 'top'
    })
    await loadClinics()
  } catch (err) {
    editError.value = err.response?.data?.detail || 'No se pudo actualizar la clínica.'
  } finally {
    editSubmitting.value = false
  }
}

function confirmToggleActive (clinic) {
  selectedClinic.value = clinic
  showToggleDialog.value = true
}

async function executeToggleActive () {
  if (!selectedClinic.value) return
  toggleSubmitting.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.patch(
      `/clinics/${selectedClinic.value.id}/toggle-active`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    showToggleDialog.value = false
    $q.notify({
      type: 'positive',
      message: data.is_active
        ? 'Sede clínica reactivada y accesos de personal restaurados.'
        : 'Sede clínica inactivada y accesos de personal suspendidos.',
      position: 'top'
    })
    await loadClinics()
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudo cambiar el estado de la clínica.',
      position: 'top'
    })
  } finally {
    toggleSubmitting.value = false
  }
}

function confirmDelete (clinic) {
  selectedClinic.value = clinic
  showDeleteDialog.value = true
}

async function executeDelete () {
  if (!selectedClinic.value) return
  deleteSubmitting.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.delete(
      `/clinics/${selectedClinic.value.id}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    showDeleteDialog.value = false
    $q.notify({
      type: 'positive',
      message: data.message || 'Tenant eliminado exitosamente.',
      position: 'top',
      timeout: 5000
    })
    await loadClinics()
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al eliminar la clínica.',
      position: 'top'
    })
  } finally {
    deleteSubmitting.value = false
  }
}

onMounted(() => {
  loadClinics()
})
</script>
