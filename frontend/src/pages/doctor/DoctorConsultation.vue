<template>
  <q-page class="p-4 md:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-5xl mx-auto space-y-6">
      <!-- Encabezado de la Consulta -->
      <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center">
            <q-icon name="clinical_notes" size="28px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900 leading-tight">Consulta Médica Especializada</h1>
            <p class="text-xs text-slate-500">Expediente Clínico Electrónico cifrado con AES-256-GCM y Receta con QR</p>
          </div>
        </div>
        <q-btn
          flat
          dense
          color="slate-600"
          icon="arrow_back"
          label="Volver a Citas"
          no-caps
          to="/appointments/my-list"
          class="self-start md:self-auto text-xs"
        />
      </div>

      <!-- Spinner de Carga de la Cita -->
      <div v-if="loadingAppointment" class="p-12 text-center bg-white rounded-2xl border border-slate-200">
        <q-spinner-dots color="teal" size="48px" />
        <p class="text-slate-500 text-xs mt-3">Cargando expediente de la cita...</p>
      </div>

      <div v-else-if="!appointment" class="p-8 text-center bg-white rounded-2xl border border-red-200">
        <q-icon name="warning" size="40px" color="negative" />
        <h2 class="text-base font-bold text-slate-800 mt-2">Cita no encontrada</h2>
        <p class="text-xs text-slate-500 mt-1">Por favor selecciona una cita válida desde la lista de gestión.</p>
        <q-btn color="primary" label="Ir a Mis Citas" no-caps to="/appointments/my-list" class="mt-4" />
      </div>

      <!-- Formulario de Consulta -->
      <form v-else @submit.prevent="submitConsultation" class="space-y-6">
        <!-- 1. Tarjeta de Datos del Paciente -->
        <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
              <q-icon name="person" size="18px" class="mr-2 text-teal-600" />
              1. Identificación del Paciente
            </h2>
            <q-badge color="teal-1" text-color="teal-9" class="font-semibold text-xs py-1 px-2.5">
              Estado: {{ appointment.status }}
            </q-badge>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div class="text-slate-400 font-medium">Paciente Titular:</div>
              <div class="font-bold text-slate-800 mt-0.5 text-sm">{{ appointment.patient_name || 'Paciente' }}</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div class="text-slate-400 font-medium">Beneficiario / Atención:</div>
              <div class="font-bold text-slate-800 mt-0.5 text-sm">
                {{ appointment.dependent_id ? 'Familiar Dependiente' : 'Titular Directo' }}
              </div>
            </div>
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div class="text-slate-400 font-medium">Sede Clínica:</div>
              <div class="font-bold text-slate-800 mt-0.5 text-sm">{{ appointment.clinic_name || 'Sede Principal' }}</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div class="text-slate-400 font-medium">Fecha y Turno:</div>
              <div class="font-bold text-slate-800 mt-0.5 text-sm">
                {{ formatDateTime(appointment.start_time) }}
              </div>
            </div>
          </div>

          <div v-if="appointment.reason" class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start">
            <q-icon name="info" size="16px" class="mr-2 mt-0.5 text-amber-600" />
            <div>
              <span class="font-bold">Motivo reportado por el paciente al agendar:</span> "{{ appointment.reason }}"
            </div>
          </div>
        </div>

        <!-- 2. Historia Clínica Estructurada (Anamnesis y Examen Físico) -->
        <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-5">
          <div class="border-b border-slate-100 pb-3 flex items-center justify-between">
            <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
              <q-icon name="edit_note" size="18px" class="mr-2 text-teal-600" />
              2. Anamnesis y Exploración Clínica (Cifrado AES-256-GCM)
            </h2>
            <div class="flex items-center text-2xs text-teal-700 bg-teal-50 py-1 px-2 rounded-lg font-medium">
              <q-icon name="lock" size="12px" class="mr-1" />
              Cifrado en Reposo por Sede
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Motivo de Consulta y Enfermedad Actual (Anamnesis) *
              </label>
              <q-input
                v-model="form.anamnesis"
                outlined
                type="textarea"
                rows="3"
                placeholder="Describir síntomas principales, tiempo de evolución, antecedentes ginecológicos (menarquía, ciclos, gestas, partos, cesáreas, abortos) y antecedentes personales."
                required
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Examen Físico y Signos Vitales (Opcional)
              </label>
              <q-input
                v-model="form.physical_exam"
                outlined
                type="textarea"
                rows="2"
                placeholder="Tensión Arterial, FC, Peso, Talla, examen mamario, abdomen, especuloscopia, tacto bimanual y hallazgos relevantes."
              />
            </div>
          </div>
        </div>

        <!-- 3. Diagnóstico CIE-10 y Conducta Médica -->
        <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-5">
          <div class="border-b border-slate-100 pb-3">
            <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
              <q-icon name="medical_services" size="18px" class="mr-2 text-teal-600" />
              3. Diagnóstico y Plan Terapéutico
            </h2>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Clasificación CIE-10 / ICD-10 Frecuente
              </label>
              <q-select
                v-model="selectedIcd10"
                :options="icd10Presets"
                option-label="label"
                outlined
                dense
                emit-value
                map-options
                placeholder="Seleccionar diagnóstico estándar..."
                @update:model-value="onIcd10Selected"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Código CIE-10 Seleccionado
              </label>
              <div class="flex gap-2">
                <q-input v-model="form.icd10_code" outlined dense placeholder="Ej. Z01.4" class="w-32" />
                <q-input v-model="form.icd10_description" outlined dense placeholder="Descripción CIE-10" class="flex-1" />
              </div>
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">
              Diagnóstico Clínico Detallado *
            </label>
            <q-input
              v-model="form.diagnosis"
              outlined
              type="textarea"
              rows="2"
              placeholder="Diagnóstico presuntivo o definitivo, estadio, hallazgos de imagen."
              required
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">
              Conducta Médica y Plan de Tratamiento *
            </label>
            <q-input
              v-model="form.plan"
              outlined
              type="textarea"
              rows="3"
              placeholder="Recomendaciones higiénico-dietéticas, solicitud de paraclínicos (ecografía transvaginal, citología, mamografía), fecha de reevaluación."
              required
            />
          </div>
        </div>

        <!-- 4. Emisión de Receta Médica con Código QR -->
        <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
                <q-icon name="receipt_long" size="18px" class="mr-2 text-teal-600" />
                4. Receta Médica Digital con Código QR (SHA-256)
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">Permite a las farmacias validar la autenticidad sin acceder a datos íntimos.</p>
            </div>
            <q-toggle
              v-model="includePrescription"
              label="Emitir Receta"
              color="teal"
              left-label
              class="text-xs font-semibold text-slate-700"
            />
          </div>

          <div v-if="includePrescription" class="space-y-4">
            <div class="space-y-3">
              <div
                v-for="(item, idx) in prescriptionItems"
                :key="idx"
                class="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 relative"
              >
                <div class="flex items-center justify-between">
                  <span class="text-xs font-bold text-teal-700">Fármaco #{{ idx + 1 }}</span>
                  <q-btn
                    v-if="prescriptionItems.length > 1"
                    flat
                    round
                    dense
                    color="negative"
                    icon="delete"
                    size="sm"
                    @click="removeItem(idx)"
                  />
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Medicamento / Principio Activo *</label>
                    <q-input v-model="item.medication" outlined dense placeholder="Ej. Ibuprofeno, Progesterona" required />
                  </div>
                  <div>
                    <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Dosis / Concentración *</label>
                    <q-input v-model="item.dosage" outlined dense placeholder="Ej. 600 mg, 100 mcg" required />
                  </div>
                  <div>
                    <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Frecuencia *</label>
                    <q-input v-model="item.frequency" outlined dense placeholder="Ej. Cada 8 horas, Diario" required />
                  </div>
                  <div>
                    <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Duración *</label>
                    <q-input v-model="item.duration" outlined dense placeholder="Ej. 5 días, 1 mes" required />
                  </div>
                </div>

                <div>
                  <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Indicaciones Específicas / Vía</label>
                  <q-input v-model="item.instructions" outlined dense placeholder="Ej. Vía oral después del desayuno" />
                </div>
              </div>

              <div class="flex justify-start">
                <q-btn
                  outline
                  color="teal"
                  icon="add"
                  label="Agregar Otro Medicamento"
                  no-caps
                  dense
                  class="text-xs font-semibold px-3 py-1"
                  @click="addItem"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div>
                <label class="block text-xs font-bold text-slate-700 mb-1">Vigencia de la Receta</label>
                <q-select
                  v-model="prescriptionDurationDays"
                  :options="[
                    { label: '30 Días (Estándar)', value: 30 },
                    { label: '60 Días', value: 60 },
                    { label: '90 Días (Tratamiento Prolongado)', value: 90 },
                    { label: '15 Días', value: 15 }
                  ]"
                  option-label="label"
                  option-value="value"
                  emit-value
                  map-options
                  outlined
                  dense
                />
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-700 mb-1">Notas Generales de la Receta</label>
                <q-input
                  v-model="prescriptionNotes"
                  outlined
                  dense
                  placeholder="Ej. Mantener hidratación adecuada. Tomar con abundante agua."
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Botón de Confirmación y Cierre de Consulta -->
        <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200">
          <div class="text-xs text-slate-500 flex items-center">
            <q-icon name="security" size="18px" class="mr-1.5 text-teal-600" />
            Al guardar, la cita pasa a estado <b>COMPLETED</b> y se genera el registro inmutable de auditoría.
          </div>

          <div class="flex items-center space-x-3 w-full sm:w-auto">
            <q-btn
              flat
              color="slate-600"
              label="Cancelar"
              no-caps
              to="/appointments/my-list"
              class="w-full sm:w-auto"
            />
            <q-btn
              color="primary"
              icon="check_circle"
              label="Finalizar y Firmar Consulta"
              no-caps
              type="submit"
              class="w-full sm:w-auto font-bold px-6 py-2.5 shadow-md"
              :loading="submitting"
            />
          </div>
        </div>
      </form>
    </div>

    <!-- Modal de Éxito con Descarga de Receta -->
    <q-dialog v-model="showSuccessModal" persistent>
      <q-card style="min-width: 420px; border-radius: 18px;" class="p-2">
        <q-card-section class="text-center pt-6 pb-2">
          <div class="w-16 h-16 rounded-full bg-teal-50 text-teal-600 mx-auto flex items-center justify-center mb-3">
            <q-icon name="verified" size="36px" />
          </div>
          <h3 class="text-lg font-bold text-slate-900">¡Consulta Finalizada Exitosamente!</h3>
          <p class="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            La historia médica fue cifrada con AES-256-GCM y guardada en el expediente electrónico.
          </p>
        </q-card-section>

        <q-card-section v-if="createdRecord?.prescriptions?.length" class="p-4 bg-slate-50 rounded-xl m-4 border border-slate-200 text-center space-y-3">
          <div class="text-xs font-bold text-slate-800">Receta Médica Oficial Generada</div>
          <div class="text-2xs text-slate-500">
            Folio: <span class="font-mono font-bold text-teal-700">{{ createdRecord.prescriptions[0].prescription_code }}</span>
          </div>

          <div class="flex justify-center gap-2 pt-1">
            <q-btn
              color="teal"
              icon="picture_as_pdf"
              label="Descargar Receta PDF"
              no-caps
              dense
              class="text-xs px-3 py-1.5 font-bold shadow-sm"
              @click="downloadPdf(createdRecord.prescriptions[0].id)"
            />
            <q-btn
              outline
              color="slate-700"
              icon="qr_code"
              label="Ver QR Público"
              no-caps
              dense
              class="text-xs px-3 py-1.5 font-semibold"
              @click="openQrPublic(createdRecord.prescriptions[0].verification_hash)"
            />
          </div>
        </q-card-section>

        <q-card-actions align="center" class="pb-6">
          <q-btn
            color="primary"
            label="Volver a la Lista de Citas"
            no-caps
            class="px-6 font-bold"
            to="/appointments/my-list"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from 'boot/axios'
import { Notify } from 'quasar'

const route = useRoute()
const router = useRouter()

const appointmentId = ref(route.query.appointment_id || '')
const appointment = ref(null)
const loadingAppointment = ref(true)
const submitting = ref(false)
const showSuccessModal = ref(false)
const createdRecord = ref(null)

const includePrescription = ref(true)
const prescriptionDurationDays = ref(30)
const prescriptionNotes = ref('')

const form = ref({
  anamnesis: '',
  physical_exam: '',
  diagnosis: '',
  plan: '',
  icd10_code: '',
  icd10_description: ''
})

const prescriptionItems = ref([
  {
    medication: '',
    dosage: '',
    frequency: '',
    duration: '',
    instructions: ''
  }
])

const icd10Presets = [
  { label: 'Z01.4 - Examen ginecológico general de rutina', code: 'Z01.4', desc: 'Examen ginecológico general' },
  { label: 'N94.4 - Dismenorrea primaria', code: 'N94.4', desc: 'Dismenorrea primaria' },
  { label: 'N94.6 - Dismenorrea no especificada', code: 'N94.6', desc: 'Dismenorrea no especificada' },
  { label: 'N92.0 - Menorragia o menstruación excesiva', code: 'N92.0', desc: 'Menstruación excesiva y frecuente' },
  { label: 'N76.0 - Vaginitis aguda', code: 'N76.0', desc: 'Vaginitis aguda' },
  { label: 'N80.0 - Endometriosis del útero', code: 'N80.0', desc: 'Endometriosis del útero' },
  { label: 'Z34.0 - Supervisión de primer embarazo normal', code: 'Z34.0', desc: 'Supervisión de primer embarazo normal' },
  { label: 'N95.1 - Síntomas menopáusicos y climatéricos', code: 'N95.1', desc: 'Estados menopáusicos y climatéricos' },
  { label: 'Z30.0 - Asesoramiento sobre anticoncepción', code: 'Z30.0', desc: 'Consejo y asesoramiento general sobre la anticoncepción' },
  { label: 'R10.2 - Dolor pélvico y perineal', code: 'R10.2', desc: 'Dolor pélvico y perineal' }
]

const selectedIcd10 = ref(null)

function onIcd10Selected (preset) {
  if (!preset) return
  form.value.icd10_code = preset.code
  form.value.icd10_description = preset.desc
  if (!form.value.diagnosis) {
    form.value.diagnosis = preset.desc
  }
}

function addItem () {
  prescriptionItems.value.push({
    medication: '',
    dosage: '',
    frequency: '',
    duration: '',
    instructions: ''
  })
}

function removeItem (index) {
  if (prescriptionItems.value.length > 1) {
    prescriptionItems.value.splice(index, 1)
  }
}

function formatDateTime (iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function fetchAppointment () {
  if (!appointmentId.value) {
    loadingAppointment.value = false
    return
  }
  loadingAppointment.value = true
  try {
    const { data } = await api.get('/appointments')
    const match = data.find(a => a.id === appointmentId.value)
    if (match) {
      appointment.value = match
    } else {
      Notify.create({ type: 'warning', message: 'No se encontró la cita especificada.' })
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al consultar datos de la cita.' })
  } finally {
    loadingAppointment.value = false
  }
}

async function submitConsultation () {
  submitting.value = true
  try {
    const payload = {
      appointment_id: appointmentId.value,
      anamnesis: form.value.anamnesis,
      physical_exam: form.value.physical_exam || undefined,
      diagnosis: form.value.diagnosis,
      plan: form.value.plan,
      icd10_code: form.value.icd10_code || undefined,
      icd10_description: form.value.icd10_description || undefined
    }

    if (includePrescription.value) {
      const validItems = prescriptionItems.value.filter(i => i.medication && i.dosage)
      if (validItems.length === 0) {
        Notify.create({ type: 'warning', message: 'Indica al menos un medicamento en la receta o desactiva la opción.' })
        submitting.value = false
        return
      }

      payload.prescription = {
        items: validItems,
        diagnosis_summary: form.value.icd10_description || form.value.diagnosis,
        notes: prescriptionNotes.value || undefined,
        duration_days: prescriptionDurationDays.value
      }
    }

    const { data } = await api.post('/medical-records', payload)
    createdRecord.value = data
    showSuccessModal.value = true
    Notify.create({
      type: 'positive',
      message: 'Consulta médica registrada y firmada con éxito.'
    })
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al registrar historia clínica.'
    })
  } finally {
    submitting.value = false
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

function openQrPublic (hash) {
  const routeData = router.resolve({ path: `/verify-prescription/${hash}` })
  window.open(routeData.href, '_blank')
}

onMounted(() => {
  fetchAppointment()
})
</script>
