<template>
  <q-page class="p-6 max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div>
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold">
            <q-icon name="point_of_sale" size="22px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">Control de Caja y Cobros Manuales</h1>
            <p class="text-xs text-slate-500">
              Gestión de recibos físicos, métodos de pago externos y balance diario de caja.
            </p>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <q-input
          v-model="selectedDate"
          type="date"
          dense
          outlined
          label="Fecha de Caja"
          @update:model-value="loadData"
        />
        <q-btn
          outline
          color="primary"
          icon="refresh"
          label="Actualizar"
          no-caps
          :loading="loading"
          @click="loadData"
        />
      </div>
    </div>

    <!-- Daily Summary Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Card Total -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium">
          <span>Total Recaudado</span>
          <q-icon name="payments" size="20px" class="text-emerald-600" />
        </div>
        <div class="text-2xl font-black text-slate-900">
          ${{ summary.total_collected || '0.00' }} <span class="text-xs font-normal text-slate-400">USD</span>
        </div>
        <div class="text-2xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-medium inline-block">
          {{ summary.paid_count }} citas cobradas hoy
        </div>
      </div>

      <!-- Card Desglose Efectivo -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium">
          <span>Efectivo (Cash)</span>
          <q-icon name="attach_money" size="20px" class="text-teal-600" />
        </div>
        <div class="text-2xl font-black text-slate-900">
          ${{ summary.by_method?.CASH || '0.00' }}
        </div>
        <div class="text-2xs text-slate-400">Físico en gaveta</div>
      </div>

      <!-- Card Transferencias / Pago Móvil / Zelle -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium">
          <span>Bancos / Electrónico</span>
          <q-icon name="account_balance" size="20px" class="text-indigo-600" />
        </div>
        <div class="text-2xl font-black text-slate-900">
          ${{ electronicTotal }}
        </div>
        <div class="text-2xs text-slate-400">Transf, Zelle, Pago Móvil</div>
      </div>

      <!-- Card Exentas / Canceladas -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium">
          <span>Exentas / Anuladas</span>
          <q-icon name="block" size="20px" class="text-rose-500" />
        </div>
        <div class="text-2xl font-black text-slate-900">
          {{ (summary.exempt_count || 0) + (summary.void_count || 0) }}
        </div>
        <div class="text-2xs text-rose-700 bg-rose-50 px-2 py-0.5 rounded font-medium inline-block">
          Excluidas de totales contables
        </div>
      </div>
    </div>

    <!-- Appointments Table for Selected Date -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div class="p-5 border-b border-slate-100 flex items-center justify-between">
        <h2 class="font-bold text-slate-800 text-base">Citas del Día y Estado de Cobro</h2>
        <span class="text-xs text-slate-400">{{ appointments.length }} registros</span>
      </div>

      <div v-if="loading" class="flex justify-center p-12">
        <q-spinner-dots color="primary" size="36px" />
      </div>

      <div v-else-if="appointments.length === 0" class="p-8 text-center text-xs text-slate-400">
        No se encontraron citas agendadas para esta fecha.
      </div>

      <div v-else class="divide-y divide-slate-100">
        <div
          v-for="app in appointments"
          :key="app.id"
          class="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-slate-50 transition-colors"
        >
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-900 text-sm">
                {{ app.patient_name || 'Paciente' }}
              </span>
              <span
                :class="statusBadge(app.payment_status)"
                class="px-2 py-0.5 rounded text-2xs font-bold uppercase"
              >
                {{ app.payment_status }}
              </span>
            </div>
            <div class="text-xs text-slate-500 mt-0.5">
              Médico: <span class="text-slate-700 font-medium">{{ app.doctor_name }}</span>
              <span class="mx-2">•</span>
              Hora: <span class="font-semibold text-slate-700">{{ formatTime(app.start_time) }} - {{ formatTime(app.end_time) }}</span>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <div class="text-right">
              <div class="text-base font-black text-slate-900">
                ${{ app.payment_amount || '0.00' }} {{ app.currency || 'USD' }}
              </div>
              <div class="text-2xs text-slate-400">{{ app.status }}</div>
            </div>

            <q-btn
              v-if="app.payment_status === 'UNPAID'"
              color="primary"
              icon="paid"
              label="Cobrar"
              no-caps
              dense
              class="px-3 py-1 text-xs font-semibold shadow-sm"
              @click="openPaymentModal(app)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Cobro Manual -->
    <q-dialog v-model="showPaymentModal">
      <q-card style="min-width: 440px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-teal-700 to-cyan-800 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="point_of_sale" size="24px" />
            <h3 class="text-base font-bold">Registrar Cobro en Ventanilla</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6 space-y-4">
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
            <div class="text-slate-500">Paciente: <span class="font-bold text-slate-800">{{ currentApp?.patient_name }}</span></div>
            <div class="text-slate-500 mt-1">Especialista: <span class="font-medium text-slate-700">{{ currentApp?.doctor_name }}</span></div>
          </div>

          <form class="space-y-3" @submit.prevent="submitPayment">
            <q-input
              v-model="payForm.amount"
              type="number"
              step="0.01"
              label="Monto Cobrado (USD) *"
              filled
              required
            />
            <q-select
              v-model="payForm.payment_method"
              :options="[
                { label: 'Efectivo (Cash)', value: 'CASH' },
                { label: 'Punto de Venta / Tarjeta', value: 'CARD' },
                { label: 'Transferencia Bancaria', value: 'TRANSFER' },
                { label: 'Pago Móvil', value: 'PAGO_MOVIL' },
                { label: 'Zelle', value: 'ZELLE' }
              ]"
              emit-value
              map-options
              label="Método de Pago *"
              filled
              required
            />
            <q-input
              v-model="payForm.reference"
              label="Número de Referencia / Comprobante"
              placeholder="Ej. REF-88392"
              filled
            />
            <q-input
              v-model="payForm.notes"
              label="Observaciones de Caja (Opcional)"
              filled
            />

            <div class="pt-2 flex justify-end space-x-2">
              <q-btn flat label="Cancelar" v-close-popup no-caps />
              <q-btn
                type="submit"
                color="primary"
                label="Confirmar Cobro"
                no-caps
                class="font-semibold"
                :loading="submittingPay"
              />
            </div>
          </form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'

const { user } = useAcl()
const DEFAULT_CLINIC_ID = 'c1111111-1111-1111-1111-111111111111'
const clinicId = user.value?.clinicId || DEFAULT_CLINIC_ID

const selectedDate = ref(new Date().toISOString().substring(0, 10))
const loading = ref(false)
const appointments = ref([])
const summary = ref({})

const showPaymentModal = ref(false)
const currentApp = ref(null)
const submittingPay = ref(false)

const payForm = reactive({
  amount: 35.00,
  payment_method: 'CASH',
  reference: '',
  notes: ''
})

const electronicTotal = computed(() => {
  const m = summary.value?.by_method || {}
  const sum = (Number(m.TRANSFER) || 0) + (Number(m.PAGO_MOVIL) || 0) + (Number(m.ZELLE) || 0) + (Number(m.CARD) || 0)
  return sum.toFixed(2)
})

async function loadData () {
  loading.value = true
  try {
    const [appsResp, sumResp] = await Promise.all([
      api.get(`/appointments?clinic_id=${clinicId}&date=${selectedDate.value}`),
      api.get(`/clinics/${clinicId}/cashier/daily-summary?date=${selectedDate.value}`)
    ])
    appointments.value = appsResp.data
    summary.value = sumResp.data
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al consultar datos de caja.' })
  } finally {
    loading.value = false
  }
}

function openPaymentModal (app) {
  currentApp.value = app
  payForm.amount = Number(app.payment_amount) || 35.00
  payForm.payment_method = 'CASH'
  payForm.reference = ''
  payForm.notes = ''
  showPaymentModal.value = true
}

async function submitPayment () {
  if (!currentApp.value) return
  submittingPay.value = true
  try {
    await api.post(`/clinics/${clinicId}/payments/${currentApp.value.id}/record`, payForm)
    Notify.create({ type: 'positive', message: '¡Cobro registrado exitosamente en caja!' })
    showPaymentModal.value = false
    await loadData()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Error al procesar cobro.' })
  } finally {
    submittingPay.value = false
  }
}

function formatTime (isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
}

function statusBadge (s) {
  if (s === 'PAID') return 'bg-emerald-100 text-emerald-800'
  if (s === 'UNPAID') return 'bg-amber-100 text-amber-800'
  if (s === 'EXEMPT') return 'bg-slate-100 text-slate-700'
  if (s === 'VOID') return 'bg-rose-100 text-rose-800'
  return 'bg-slate-100 text-slate-800'
}

onMounted(() => {
  loadData()
})
</script>
