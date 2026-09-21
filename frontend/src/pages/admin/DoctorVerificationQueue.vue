<template>
  <q-page class="p-6 bg-slate-50 min-h-screen">
    <div class="max-w-6xl mx-auto space-y-6">
      <!-- Header -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center space-x-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              Supervisión de Cumplimiento
            </span>
            <span class="text-xs text-slate-400">HIPAA / GDPR / Leyes Médicas</span>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 mt-1">Cola de Verificación de Matrículas</h1>
          <p class="text-sm text-slate-500 mt-0.5">
            Revisión y acreditación de credenciales médicas para habilitar disponibilidad y citas públicas.
          </p>
        </div>

        <div class="flex items-center space-x-3">
          <q-btn
            outline
            color="primary"
            icon="refresh"
            label="Actualizar"
            no-caps
            :loading="loading"
            @click="loadQueue"
          />
        </div>
      </div>

      <!-- Buscador y Filtros -->
      <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-200/80 flex items-center gap-4">
        <q-input
          v-model="searchQuery"
          dense
          outlined
          placeholder="Buscar por médico, matrícula o especialidad..."
          class="flex-1"
        >
          <template #prepend>
            <q-icon name="search" size="18px" />
          </template>
        </q-input>
      </div>

      <!-- Tabla o Lista de Médicos Pendientes -->
      <div class="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden">
        <div v-if="loading" class="text-center py-16">
          <q-spinner-dots color="primary" size="48px" />
          <p class="text-slate-500 mt-3 text-sm">Cargando médicos en espera de validación...</p>
        </div>

        <div v-else-if="filteredDoctors.length === 0" class="text-center py-16 px-4">
          <div class="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
            <q-icon name="task_alt" size="36px" />
          </div>
          <h3 class="text-lg font-semibold text-slate-800">¡Al día! No hay verificaciones pendientes</h3>
          <p class="text-slate-500 text-sm mt-1 max-w-md mx-auto">
            Todos los médicos registrados en la plataforma tienen su matrícula validada o no hay nuevas solicitudes en cola.
          </p>
        </div>

        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="doctor in filteredDoctors"
            :key="doctor.id"
            class="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/80 transition-colors"
          >
            <div class="flex items-start space-x-4">
              <div class="w-12 h-12 rounded-xl bg-blue-100/70 text-blue-700 flex items-center justify-center font-bold text-lg">
                <q-icon name="medical_services" size="24px" />
              </div>

              <div>
                <div class="flex items-center space-x-2">
                  <h3 class="font-bold text-slate-900 text-base">
                    {{ doctor.full_name || 'Nombre no registrado' }}
                  </h3>
                  <span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">
                    Pendiente Verificación
                  </span>
                </div>

                <div class="text-xs text-slate-500 mt-1 flex flex-wrap gap-x-4 gap-y-1">
                  <span><q-icon name="email" size="14px" class="mr-1" />{{ doctor.email }}</span>
                  <span v-if="doctor.phone"><q-icon name="phone" size="14px" class="mr-1" />{{ doctor.phone }}</span>
                  <span v-if="Array.isArray(doctor.specialties) && doctor.specialties.length > 0" class="flex items-center gap-1 text-slate-700 font-medium">
                    <q-icon name="local_offer" size="14px" class="text-teal-600" />
                    <span>{{ doctor.specialties.join(', ') }}</span>
                  </span>
                  <span v-else-if="doctor.specialty" class="text-slate-700 font-medium">
                    <q-icon name="local_offer" size="14px" class="mr-1 text-teal-600" />{{ doctor.specialty }}
                  </span>
                </div>

                <div class="mt-2 text-xs text-slate-600">
                  <span>Matrícula Declarada: </span>
                  <strong class="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-800">
                    {{ doctor.license_number || 'No especificada' }}
                  </strong>
                </div>
              </div>
            </div>

            <div class="flex items-center space-x-3 self-end md:self-center">
              <q-btn
                color="primary"
                label="Revisar y Dictaminar"
                icon="verified_user"
                no-caps
                class="font-semibold px-4"
                @click="openReviewModal(doctor)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Revisión y Dictamen -->
    <q-dialog v-model="showReviewDialog" persistent>
      <q-card style="min-width: 480px; max-width: 600px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-slate-900 to-slate-800 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="fact_check" size="24px" class="text-teal-400" />
            <h3 class="text-lg font-bold">Dictamen de Matrícula Médica</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6 space-y-4" v-if="selectedDoctor">
          <!-- Tarjeta de Datos -->
          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 text-sm space-y-2">
            <div class="flex justify-between">
              <span class="text-slate-500">Médico:</span>
              <strong class="text-slate-900">{{ selectedDoctor.full_name || selectedDoctor.email }}</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Correo:</span>
              <span class="text-slate-800">{{ selectedDoctor.email }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Especialidad(es):</span>
              <strong class="text-teal-700">{{ (Array.isArray(selectedDoctor.specialties) && selectedDoctor.specialties.length > 0) ? selectedDoctor.specialties.join(', ') : (selectedDoctor.specialty || 'General') }}</strong>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-500">Colegiatura / Matrícula:</span>
              <span class="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 font-bold text-slate-900">
                {{ selectedDoctor.license_number || 'N/A' }}
              </span>
            </div>
          </div>

          <!-- Documento Adjunto -->
          <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-100 flex items-center justify-between text-xs text-blue-900">
            <div class="flex items-center space-x-2">
              <q-icon name="attach_file" size="18px" class="text-blue-600" />
              <span>Documento de Respaldo:</span>
            </div>
            <a
              v-if="selectedDoctor.license_document_url"
              :href="selectedDoctor.license_document_url"
              target="_blank"
              class="font-semibold text-blue-700 hover:underline flex items-center"
            >
              Ver Adjunto <q-icon name="open_in_new" size="14px" class="ml-1" />
            </a>
            <span v-else class="text-slate-500 italic">Validación por registro público</span>
          </div>

          <!-- Motivo o Justificación -->
          <div class="space-y-1">
            <label class="text-xs font-semibold text-slate-700">Motivo / Justificación del Dictamen (quedará en Audit Trail):</label>
            <q-input
              v-model="reviewReason"
              type="textarea"
              rows="3"
              outlined
              dense
              placeholder="Ej. Matrícula confirmada en el registro del Colegio Médico Nacional..."
            />
          </div>

          <div v-if="actionError" class="p-3 rounded-lg bg-red-50 text-red-700 text-xs flex items-center">
            <q-icon name="warning" class="mr-2" size="16px" />
            <span>{{ actionError }}</span>
          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="between" class="p-4 bg-slate-50">
          <q-btn
            outline
            color="negative"
            label="Rechazar Matrícula"
            icon="cancel"
            no-caps
            :loading="submittingAction"
            @click="submitDecision('REJECT')"
          />

          <q-btn
            color="positive"
            label="Aprobar y Activar Médico"
            icon="verified"
            no-caps
            class="font-semibold px-4"
            :loading="submittingAction"
            @click="submitDecision('APPROVE')"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from 'boot/axios'

const loading = ref(false)
const doctors = ref([])
const searchQuery = ref('')

const showReviewDialog = ref(false)
const selectedDoctor = ref(null)
const reviewReason = ref('')
const submittingAction = ref(false)
const actionError = ref('')

const filteredDoctors = computed(() => {
  if (!searchQuery.value.trim()) return doctors.value
  const q = searchQuery.value.toLowerCase()
  return doctors.value.filter(
    d =>
      (d.full_name && d.full_name.toLowerCase().includes(q)) ||
      (d.email && d.email.toLowerCase().includes(q)) ||
      (Array.isArray(d.specialties) && d.specialties.some(s => s && s.toLowerCase().includes(q))) ||
      (d.specialty && d.specialty.toLowerCase().includes(q)) ||
      (d.license_number && d.license_number.toLowerCase().includes(q))
  )
})

async function loadQueue() {
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.get('/doctors/pending-verification', {
      headers: { Authorization: `Bearer ${token}` }
    })
    doctors.value = data
  } catch (err) {
    console.error('Error al cargar cola de verificación:', err)
  } finally {
    loading.value = false
  }
}

function openReviewModal(doctor) {
  selectedDoctor.value = doctor
  reviewReason.value = ''
  actionError.value = ''
  showReviewDialog.value = true
}

async function submitDecision(action) {
  if (action === 'REJECT' && !reviewReason.value.trim()) {
    actionError.value = 'Debe indicar el motivo del rechazo para notificar al médico.'
    return
  }

  submittingAction.value = true
  actionError.value = ''

  try {
    const token = localStorage.getItem('access_token')
    await api.post(
      `/doctors/${selectedDoctor.value.id}/verify`,
      {
        action: action,
        reason: reviewReason.value.trim() || undefined
      },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )

    showReviewDialog.value = false
    await loadQueue()
  } catch (err) {
    actionError.value = err.response?.data?.detail || 'Ocurrió un error al procesar el dictamen.'
  } finally {
    submittingAction.value = false
  }
}

onMounted(() => {
  loadQueue()
})
</script>
