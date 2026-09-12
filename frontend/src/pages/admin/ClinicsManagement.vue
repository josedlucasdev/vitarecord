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
            Aprovisionamiento, activación y configuración de sedes clínicas en la plataforma ÍntimaSalud.
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
              <div class="w-12 h-12 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center font-bold text-lg">
                <q-icon name="apartment" size="24px" />
              </div>

              <div>
                <div class="flex items-center space-x-2">
                  <h3 class="font-bold text-slate-900 text-base">{{ clinic.name }}</h3>
                  <span
                    class="px-2 py-0.5 rounded text-xs font-semibold"
                    :class="clinic.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'"
                  >
                    {{ clinic.is_active ? 'Activa' : 'Inactiva' }}
                  </span>
                </div>

                <div class="text-xs text-slate-500 mt-1 flex flex-wrap gap-x-4 gap-y-1">
                  <span><strong>ID:</strong> <code class="font-mono">{{ clinic.id }}</code></span>
                  <span><strong>Slug:</strong> {{ clinic.slug }}</span>
                  <span><strong>Zona Horaria:</strong> {{ clinic.timezone }}</span>
                  <span><strong>País:</strong> {{ clinic.country_code }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center space-x-2 self-end md:self-center">
              <q-badge outline color="primary" label="Tenant Aislado" class="px-2 py-1 text-xs" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Crear Nueva Clínica -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 440px; max-width: 500px; border-radius: 16px;">
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
              label="Nombre de la Clínica (ej. Clínica ÍntimaSalud Este)"
              filled
              required
              @update:model-value="autoGenerateSlug"
            />
            <q-input
              v-model="formSlug"
              label="Slug único de acceso (ej. intimasalud-este)"
              filled
              hint="Se usará como subdominio o identificador de tenant"
              required
            />
            <q-input
              v-model="formTimezone"
              label="Zona Horaria (ej. America/Caracas)"
              filled
              required
            />
            <q-input
              v-model="formCountry"
              label="Código de País (ej. VE, CO, ES, US)"
              filled
              maxlength="2"
              required
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
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from 'boot/axios'

const clinics = ref([])
const loading = ref(false)

const showCreateDialog = ref(false)
const formName = ref('')
const formSlug = ref('')
const formTimezone = ref('America/Caracas')
const formCountry = ref('VE')
const submitting = ref(false)
const createError = ref('')

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
  } finally {
    loading.value = false
  }
}

function openCreateModal () {
  formName.value = ''
  formSlug.value = ''
  formTimezone.value = 'America/Caracas'
  formCountry.value = 'VE'
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
        country_code: formCountry.value.toUpperCase()
      },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    showCreateDialog.value = false
    await loadClinics()
  } catch (err) {
    createError.value = err.response?.data?.detail || 'No se pudo crear la clínica.'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadClinics()
})
</script>
