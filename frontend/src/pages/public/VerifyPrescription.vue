<template>
  <q-layout view="lHh Lpr lFf" class="bg-slate-100 min-h-screen">
    <q-page-container>
      <q-page class="p-4 md:p-10 flex items-center justify-center">
        <div class="w-full max-w-2xl bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden">
          <!-- Banner Superior -->
          <div class="bg-gradient-to-r from-teal-800 to-cyan-900 text-white p-6 sm:p-8 text-center relative">
            <div class="inline-flex p-2.5 bg-white rounded-2xl mb-3 shadow-md border border-white/30">
              <img src="/icons/vitarecord-logo.png" alt="VitaRecord" class="w-12 h-12 object-contain" />
            </div>
            <h1 class="text-xl sm:text-2xl font-bold tracking-tight">Verificación de Receta Médica</h1>
            <p class="text-xs text-teal-100 mt-1 max-w-md mx-auto">
              Portal Oficial de Validación Farmacéutica Criptográfica — Plataforma VitaRecord
            </p>
          </div>

          <!-- Spinner de Carga -->
          <div v-if="loading" class="p-12 text-center">
            <q-spinner-dots color="teal" size="48px" />
            <p class="text-xs text-slate-500 mt-3">Validando firma criptográfica SHA-256...</p>
          </div>

          <!-- Error / Receta No Encontrada -->
          <div v-else-if="error || !prescription" class="p-8 text-center space-y-3">
            <div class="w-16 h-16 rounded-full bg-red-50 text-red-600 mx-auto flex items-center justify-center">
              <q-icon name="error_outline" size="36px" />
            </div>
            <h2 class="text-lg font-bold text-slate-900">Código de Receta No Válido</h2>
            <p class="text-xs text-slate-500 max-w-md mx-auto">
              El identificador de verificación no corresponde a una receta válida o ha sido revocado.
            </p>
            <div class="pt-2">
              <q-btn
                outline
                color="slate-700"
                label="Ir al Inicio"
                no-caps
                to="/"
                class="font-semibold text-xs px-5"
              />
            </div>
          </div>

          <!-- Datos Oficiales de la Receta -->
          <div v-else class="p-6 sm:p-8 space-y-6">
            <!-- Sello de Estado -->
            <div
              :class="[
                'p-4 rounded-2xl border flex items-center justify-between',
                prescription.is_valid
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : 'bg-red-50 border-red-200 text-red-900'
              ]"
            >
              <div class="flex items-center space-x-3">
                <q-icon
                  :name="prescription.is_valid ? 'check_circle' : 'cancel'"
                  size="28px"
                  :color="prescription.is_valid ? 'positive' : 'negative'"
                />
                <div>
                  <div class="font-bold text-sm">
                    {{ prescription.is_valid ? 'RECETA OFICIAL VIGENTE' : 'RECETA EXPIRADA / NO VÁLIDA' }}
                  </div>
                  <div class="text-2xs opacity-80">
                    {{ prescription.is_valid ? 'Acreditada para dispensación en farmacia' : 'La fecha de validez ha vencido' }}
                  </div>
                </div>
              </div>

              <span class="text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-white shadow-2xs">
                {{ prescription.prescription_code }}
              </span>
            </div>

            <!-- Datos del Facultativo y Clínica -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <div class="text-slate-400 font-semibold uppercase text-2xs">Médico Especialista</div>
                <div class="font-bold text-slate-900 text-sm">{{ prescription.doctor_name }}</div>
                <div class="text-slate-600 text-2xs">
                  {{ prescription.doctor_specialty || 'Ginecología & Obstetricia' }}
                  <span class="text-teal-700 font-bold ml-1">({{ prescription.doctor_license }})</span>
                </div>
              </div>

              <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <div class="text-slate-400 font-semibold uppercase text-2xs">Sede Emisora</div>
                <div class="font-bold text-slate-900 text-sm">{{ prescription.clinic_name }}</div>
                <div class="text-slate-600 text-2xs">Red de Centros Médicos ÍntimaSalud</div>
              </div>

              <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <div class="text-slate-400 font-semibold uppercase text-2xs">Paciente Titular</div>
                <div class="font-bold text-slate-900 text-sm">{{ prescription.patient_name }}</div>
              </div>

              <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <div class="text-slate-400 font-semibold uppercase text-2xs">Vigencia Farmacéutica</div>
                <div class="font-bold text-slate-900">
                  {{ formatDate(prescription.issued_at) }} al {{ formatDate(prescription.expires_at) }}
                </div>
              </div>
            </div>

            <!-- Tabla de Medicamentos Prescritos -->
            <div class="space-y-2">
              <h3 class="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center">
                <q-icon name="medication" size="18px" class="mr-1 text-teal-600" />
                Medicamentos Prescritos
              </h3>

              <div class="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-200">
                <div
                  v-for="(item, idx) in prescription.items"
                  :key="idx"
                  class="p-3.5 bg-white text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div>
                    <div class="font-bold text-slate-900 text-sm">
                      {{ item.medication }} <span class="text-teal-700 font-semibold">({{ item.dosage }})</span>
                    </div>
                    <div v-if="item.instructions" class="text-slate-500 text-2xs italic mt-0.5">
                      "{{ item.instructions }}"
                    </div>
                  </div>
                  <div class="text-right text-slate-600 font-medium text-2xs">
                    <div>{{ item.frequency }}</div>
                    <div class="text-slate-400">Duración: {{ item.duration }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Pie Legal de Seguridad -->
            <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 text-center text-2xs text-slate-500 space-y-1">
              <div class="font-bold text-slate-700">Validación Criptográfica en Tiempo Real</div>
              <div>Token SHA-256 verificado contra los servidores de ÍntimaSalud.</div>
              <div class="text-slate-400 font-mono text-3xs truncate mt-0.5">Hash: {{ verificationHash }}</div>
            </div>
          </div>
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'boot/axios'

const route = useRoute()
const verificationHash = ref(route.params.hash || '')
const prescription = ref(null)
const loading = ref(true)
const error = ref(false)

function formatDate (iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

async function verifyPrescription () {
  if (!verificationHash.value) {
    loading.value = false
    error.value = true
    return
  }
  loading.value = true
  try {
    const { data } = await api.get(`/medical-records/prescriptions/verify/${verificationHash.value}`)
    prescription.value = data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  verifyPrescription()
})
</script>
