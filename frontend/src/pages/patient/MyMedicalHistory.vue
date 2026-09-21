<template>
  <q-page class="p-4 md:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-5xl mx-auto space-y-6">
      <!-- Encabezado -->
      <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center">
            <q-icon name="folder_shared" size="28px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900 leading-tight">Mi Historial Clínico</h1>
            <p class="text-xs text-slate-500">Consultas previas, diagnósticos, recetas verificables y evolución médica</p>
          </div>
        </div>

        <!-- Selector de Beneficiario (Titular o Dependientes) -->
        <div v-if="dependents.length > 0" class="w-full sm:w-64">
          <q-select
            v-model="selectedDependentId"
            :options="beneficiaryOptions"
            option-label="label"
            option-value="value"
            emit-value
            map-options
            outlined
            dense
            bg-color="white"
            label="Ver historial de"
            @update:model-value="fetchHistory"
          />
        </div>
      </div>

      <!-- Estado de Carga -->
      <div v-if="loading" class="p-12 text-center bg-white rounded-2xl border border-slate-200">
        <q-spinner-dots color="teal" size="48px" />
        <p class="text-slate-500 text-xs mt-3">Descifrando historial médico con claves de sede...</p>
      </div>

      <!-- Estado Vacío -->
      <div v-else-if="records.length === 0" class="p-12 text-center bg-white rounded-2xl border border-slate-200 space-y-3">
        <div class="w-16 h-16 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
          <q-icon name="history_edu" size="32px" />
        </div>
        <h3 class="text-base font-bold text-slate-800">No hay consultas registradas</h3>
        <p class="text-xs text-slate-500 max-w-sm mx-auto">
          Aún no se han completado consultas médicas para este paciente. Una vez que el médico finalice la atención, tu resumen y recetas aparecerán aquí.
        </p>
        <q-btn
          color="primary"
          icon="calendar_today"
          label="Agendar Nueva Cita"
          no-caps
          to="/appointments/book"
          class="font-bold text-xs px-4 py-2 mt-2"
        />
      </div>

      <!-- Listado de Historias Médicas -->
      <div v-else class="space-y-5">
        <div
          v-for="rec in records"
          :key="rec.id"
          class="bg-white rounded-2xl shadow-xs border border-slate-200 overflow-hidden transition-all hover:shadow-md"
        >
          <!-- Barra superior de la tarjeta -->
          <div class="bg-gradient-to-r from-teal-800 to-cyan-900 text-white p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div class="flex items-center space-x-3">
              <q-icon name="event" size="22px" class="text-teal-200" />
              <div>
                <div class="font-bold text-sm leading-tight">{{ formatDate(rec.created_at) }}</div>
                <div class="text-2xs text-teal-100">{{ rec.clinic_name || 'Clínica ÍntimaSalud' }}</div>
              </div>
            </div>

            <div class="flex items-center space-x-2">
              <span class="text-xs text-teal-100 font-medium">Médico:</span>
              <span class="text-xs font-bold bg-teal-700/60 px-2.5 py-1 rounded-lg border border-teal-500/30">
                {{ rec.doctor_name || 'Especialista' }}
                <span v-if="rec.doctor_specialty" class="text-teal-200 font-normal">({{ rec.doctor_specialty }})</span>
              </span>
            </div>
          </div>

          <!-- Contenido Clínico -->
          <div class="p-6 space-y-5">
            <!-- Diagnóstico y CIE-10 -->
            <div class="bg-teal-50/70 p-4 rounded-xl border border-teal-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div class="text-2xs uppercase font-bold tracking-wider text-teal-800">Diagnóstico Principal</div>
                <div class="text-sm font-bold text-teal-950 mt-0.5">{{ rec.diagnosis }}</div>
              </div>
              <div v-if="rec.icd10_code" class="self-start sm:self-auto">
                <span class="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-white text-teal-800 border border-teal-200 shadow-2xs">
                  CIE-10: {{ rec.icd10_code }}
                </span>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
              <!-- Anamnesis / Motivo -->
              <div class="space-y-1.5">
                <div class="font-bold text-slate-700 flex items-center">
                  <q-icon name="notes" size="16px" class="mr-1 text-teal-600" />
                  Motivo de Consulta y Evolución
                </div>
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-slate-700 leading-relaxed whitespace-pre-line">
                  {{ rec.anamnesis }}
                </div>
              </div>

              <!-- Plan Terapéutico -->
              <div class="space-y-1.5">
                <div class="font-bold text-slate-700 flex items-center">
                  <q-icon name="assignment" size="16px" class="mr-1 text-teal-600" />
                  Conducta Médica e Indicaciones
                </div>
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-slate-700 leading-relaxed whitespace-pre-line">
                  {{ rec.plan }}
                </div>
              </div>
            </div>

            <!-- Examen Físico si existe -->
            <div v-if="rec.physical_exam" class="text-xs space-y-1.5">
              <div class="font-bold text-slate-700 flex items-center">
                <q-icon name="monitor_heart" size="16px" class="mr-1 text-teal-600" />
                Signos Vitales y Examen Físico
              </div>
              <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-700">
                {{ rec.physical_exam }}
              </div>
            </div>

            <!-- Sección de Recetas Médicas Emitidas -->
            <div v-if="rec.prescriptions && rec.prescriptions.length > 0" class="pt-2 border-t border-slate-100 space-y-3">
              <div class="flex items-center justify-between">
                <div class="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center">
                  <q-icon name="receipt_long" size="18px" class="mr-1.5 text-teal-600" />
                  Receta Médica Digital con Código QR
                </div>
                <span class="text-2xs text-slate-400">Verificable en farmacias mediante SHA-256</span>
              </div>

              <div
                v-for="p in rec.prescriptions"
                :key="p.id"
                class="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3"
              >
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-2">
                  <div>
                    <span class="text-2xs font-semibold text-slate-500">Folio:</span>
                    <span class="text-xs font-mono font-bold text-teal-800 ml-1">{{ p.prescription_code }}</span>
                    <span class="text-2xs text-slate-400 ml-3">Vigencia hasta: {{ formatDate(p.expires_at) }}</span>
                  </div>

                  <div class="flex items-center gap-2">
                    <q-btn
                      color="teal"
                      icon="picture_as_pdf"
                      label="Descargar Receta PDF"
                      no-caps
                      dense
                      class="text-xs font-bold px-3 py-1 shadow-sm"
                      @click="downloadPdf(p.id)"
                    />
                    <q-btn
                      outline
                      color="slate-700"
                      icon="qr_code_2"
                      label="Ver QR Público"
                      no-caps
                      dense
                      class="text-xs font-semibold px-2.5 py-1"
                      @click="openQr(p.verification_hash)"
                    />
                  </div>
                </div>

                <!-- Lista de Medicamentos -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div
                    v-for="(med, mIdx) in p.items"
                    :key="mIdx"
                    class="p-2.5 bg-white rounded-lg border border-slate-200 space-y-0.5"
                  >
                    <div class="font-bold text-slate-900">{{ med.medication }} ({{ med.dosage }})</div>
                    <div class="text-slate-600 text-2xs">Frecuencia: {{ med.frequency }} | Duración: {{ med.duration }}</div>
                    <div v-if="med.instructions" class="text-slate-500 text-2xs italic">"{{ med.instructions }}"</div>
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
import { ref, computed, onMounted } from 'vue'
import { api } from 'boot/axios'
import { Notify } from 'quasar'
import { useRouter } from 'vue-router'

const router = useRouter()

const loading = ref(true)
const records = ref([])
const dependents = ref([])
const selectedDependentId = ref(null)

const beneficiaryOptions = computed(() => {
  const opts = [{ label: 'Titular Directo (Mis Consultas)', value: null }]
  dependents.value.forEach(d => {
    opts.push({
      label: `${d.full_name} (${d.relationship})`,
      value: d.id
    })
  })
  return opts
})

function formatDate (iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  })
}

async function fetchDependents () {
  try {
    const { data } = await api.get('/patients/me/dependents')
    dependents.value = Array.isArray(data) ? data : []
  } catch {
    // Si no es paciente o falla, lista vacía
    dependents.value = []
  }
}

async function fetchHistory () {
  loading.value = true
  try {
    const userRes = await api.get('/auth/me')
    const currentUserId = userRes.data.id

    let url = `/medical-records/patient/${currentUserId}`
    if (selectedDependentId.value) {
      url += `?dependent_id=${selectedDependentId.value}`
    }

    const { data } = await api.get(url)
    records.value = data
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al consultar historial clínico.'
    })
  } finally {
    loading.value = false
  }
}

async function downloadPdf (prescriptionId) {
  try {
    const resp = await api.get(`/medical-records/prescriptions/${prescriptionId}/pdf`, {
      responseType: 'blob'
    })
    const blob = new Blob([resp.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Receta_${prescriptionId.slice(0, 8)}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al descargar PDF de receta.' })
  }
}

function openQr (hash) {
  const routeData = router.resolve({ path: `/verify-prescription/${hash}` })
  window.open(routeData.href, '_blank')
}

onMounted(async () => {
  await fetchDependents()
  await fetchHistory()
})
</script>
