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
            <h1 class="text-xl font-bold text-slate-900">Control de Caja y Arqueo Diario</h1>
            <p class="text-xs text-slate-500">
              Gestión de ingresos por sede, corte del día y cobros en taquilla.
            </p>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <q-btn
          unelevated
          size="sm"
          :color="selectedDate === todayStr ? 'teal-7' : 'grey-3'"
          :text-color="selectedDate === todayStr ? 'white' : 'dark'"
          label="Hoy"
          no-caps
          class="rounded-lg px-3"
          @click="setDate(todayStr)"
        />
        <q-btn
          unelevated
          size="sm"
          :color="selectedDate === '2026-09-13' ? 'teal-7' : 'grey-3'"
          :text-color="selectedDate === '2026-09-13' ? 'white' : 'dark'"
          label="13 Sep (Cobros)"
          no-caps
          class="rounded-lg px-3"
          @click="setDate('2026-09-13')"
        />
        <q-input
          v-model="selectedDate"
          type="date"
          dense
          outlined
          label="Fecha de Corte"
          class="w-40"
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
        <q-btn
          unelevated
          color="teal-8"
          icon="file_download"
          label="Exportar Contabilidad (Excel)"
          no-caps
          class="font-semibold shadow-sm rounded-lg"
          @click="openExportModal"
        />
      </div>
    </div>

    <!-- Banner Explicativo: Caja vs Dashboard -->
    <div class="bg-gradient-to-r from-teal-50 to-indigo-50 border border-teal-200/70 p-4 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-teal-600 text-white rounded-xl shadow-xs">
          <q-icon name="info" size="20px" />
        </div>
        <div>
          <span class="font-bold text-slate-800">Corte Contable del Día Seleccionado ({{ selectedDate }}):</span>
          <p class="text-slate-600 mt-0.5">
            Esta pantalla refleja el arqueo y balance específico de la fecha elegida. En el
            <router-link to="/dashboard" class="text-teal-700 font-bold underline hover:text-teal-900">
              Dashboard de la Clínica
            </router-link>
            se consolida la recaudación mensual total (${{ Number(clinicAnalytics?.kpis?.total_revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }} USD con {{ clinicAnalytics?.kpis?.total_paid_count || 0 }} cobros).
          </p>
        </div>
      </div>
      <q-btn
        flat
        dense
        color="teal-8"
        label="Ver Dashboard General"
        icon-right="arrow_forward"
        no-caps
        to="/dashboard"
        class="font-semibold whitespace-nowrap"
      />
    </div>

    <!-- Daily Summary Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Card Total -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium">
          <span>Recaudado en Fecha</span>
          <q-icon name="payments" size="20px" class="text-emerald-600" />
        </div>
        <div class="text-2xl font-black text-slate-900">
          ${{ Number(summary.total_collected || 0).toFixed(2) }} <span class="text-xs font-normal text-slate-400">USD</span>
        </div>
        <div class="text-2xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-medium inline-block">
          {{ summary.paid_count || 0 }} pagos registrados en esta fecha
        </div>
      </div>

      <!-- Card Desglose Efectivo -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium">
          <span>Efectivo (Cash)</span>
          <q-icon name="attach_money" size="20px" class="text-teal-600" />
        </div>
        <div class="text-2xl font-black text-slate-900">
          ${{ Number(summary.by_method?.CASH || 0).toFixed(2) }}
        </div>
        <div class="text-2xs text-slate-400">Físico en gaveta / caja chica</div>
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
        <div class="text-2xs text-slate-400">Transf, Zelle, Pago Móvil, Tarjeta</div>
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
        <div>
          <h2 class="font-bold text-slate-800 text-base">Citas y Movimientos del Corte</h2>
          <p class="text-2xs text-slate-400">Citas con cobros procesados o agendadas para el {{ selectedDate }}</p>
        </div>
        <span class="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg">
          {{ appointments.length }} registros
        </span>
      </div>

      <div v-if="loading" class="flex justify-center p-12">
        <q-spinner-dots color="primary" size="36px" />
      </div>

      <div v-else-if="appointments.length === 0" class="p-12 text-center text-slate-400 space-y-2">
        <q-icon name="event_busy" size="40px" class="text-slate-300" />
        <p class="text-sm font-medium text-slate-500">No se encontraron movimientos ni citas para esta fecha.</p>
        <p class="text-xs text-slate-400">Prueba seleccionando otra fecha en el selector superior.</p>
      </div>

      <div v-else class="divide-y divide-slate-100">
        <div
          v-for="app in appointments"
          :key="app.id"
          class="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-slate-50 transition-colors"
        >
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-bold text-slate-900 text-sm">
                {{ app.patient_name || 'Paciente' }}
              </span>
              <span
                :class="statusBadge(app.payment_status)"
                class="px-2 py-0.5 rounded text-2xs font-bold uppercase"
              >
                {{ app.payment_status || 'UNPAID' }}
              </span>
              <span
                v-if="app.payment_method"
                class="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-2xs font-medium uppercase"
              >
                <q-icon name="payment" size="12px" class="mr-1" />{{ app.payment_method }}
              </span>
            </div>
            <div class="text-xs text-slate-500 mt-1">
              Médico: <span class="text-slate-700 font-medium">{{ app.doctor_name || 'Especialista' }}</span>
              <span class="mx-2">•</span>
              Fecha Cita: <span class="font-semibold text-slate-700">{{ formatDate(app.start_time) }} {{ formatTime(app.start_time) }}</span>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <div class="text-right">
              <div class="text-base font-black text-slate-900">
                ${{ Number(app.payment_amount || 30).toFixed(2) }} {{ app.currency || 'USD' }}
              </div>
              <div class="text-2xs text-slate-400">{{ app.status }}</div>
            </div>

            <q-btn
              v-if="app.payment_status === 'UNPAID' || !app.payment_status"
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
        <q-card-section class="bg-teal-600 text-white flex items-center justify-between">
          <div class="text-base font-bold flex items-center gap-2">
            <q-icon name="point_of_sale" size="20px" />
            Registrar Cobro en Taquilla
          </div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section class="p-5 space-y-4">
          <div class="p-3 bg-teal-50 border border-teal-200 rounded-xl text-xs text-teal-800 space-y-1">
            <div><strong>Paciente:</strong> {{ currentApp?.patient_name }}</div>
            <div><strong>Especialista:</strong> {{ currentApp?.doctor_name }}</div>
            <div><strong>Fecha:</strong> {{ formatDate(currentApp?.start_time) }} {{ formatTime(currentApp?.start_time) }}</div>
          </div>

          <form class="space-y-4" @submit.prevent="submitPayment">
            <q-input
              v-model.number="payForm.amount"
              type="number"
              step="0.01"
              label="Monto a Cobrar (USD) *"
              filled
              required
            />
            <q-select
              v-model="payForm.payment_method"
              :options="[
                { label: 'Efectivo (Cash)', value: 'CASH' },
                { label: 'Tarjeta de Débito / Crédito', value: 'CARD' },
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

    <!-- Modal Exportar Libro Contable para Contadores -->
    <q-dialog v-model="showExportModal">
      <q-card style="min-width: 480px; max-width: 540px; border-radius: 16px;">
        <q-card-section class="bg-teal-700 text-white flex items-center justify-between">
          <div class="text-base font-bold flex items-center gap-2">
            <q-icon name="table_view" size="22px" />
            Exportar Registro Contable en Excel
          </div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6 space-y-4">
          <div class="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 space-y-1">
            <div class="font-bold flex items-center gap-1.5 text-emerald-800">
              <q-icon name="verified" size="18px" class="text-emerald-600" />
              Estructura Fiscal para Contabilidad en Venezuela (SENIAT / VEN-NIF)
            </div>
            <p class="text-2xs text-emerald-700 leading-relaxed m-0">
              Genera un archivo Excel (.xlsx) oficial con desglose de Cédula/RIF del paciente, concepto,
              médico tratante, método de pago, condición fiscal de exención de IVA (Art. 18 Ley IVA) y conversión multimoneda a Bolívares (VES).
            </p>
          </div>

          <div class="space-y-4">
            <div>
              <div class="text-xs font-bold text-slate-700 mb-1.5">Rango de Fechas a Liquidar</div>
              <div class="grid grid-cols-2 gap-3">
                <q-input
                  v-model="exportForm.start_date"
                  type="date"
                  dense
                  outlined
                  label="Fecha Desde"
                />
                <q-input
                  v-model="exportForm.end_date"
                  type="date"
                  dense
                  outlined
                  label="Fecha Hasta"
                />
              </div>

              <div class="flex flex-wrap gap-2 pt-2">
                <q-btn
                  dense
                  unelevated
                  size="xs"
                  color="grey-2"
                  text-color="dark"
                  label="Día de Corte Actual"
                  no-caps
                  class="px-2 font-medium"
                  @click="setExportPreset('today')"
                />
                <q-btn
                  dense
                  unelevated
                  size="xs"
                  color="grey-2"
                  text-color="dark"
                  label="Últimos 30 Días"
                  no-caps
                  class="px-2 font-medium"
                  @click="setExportPreset('30days')"
                />
                <q-btn
                  dense
                  unelevated
                  size="xs"
                  color="grey-2"
                  text-color="dark"
                  label="Todo el Histórico"
                  no-caps
                  class="px-2 font-medium"
                  @click="setExportPreset('all')"
                />
              </div>
            </div>

            <div>
              <div class="text-xs font-bold text-slate-700 mb-1">Tasa Oficial BCV de Referencia (Bs./USD)</div>
              <q-input
                v-model.number="exportForm.bcv_rate"
                type="number"
                step="0.01"
                dense
                outlined
                hint="Convierte automáticamente la facturación a Bolívares según normativa SENIAT."
              />
            </div>

            <div>
              <div class="text-xs font-bold text-slate-700 mb-1">Filtro de Estado de Operación</div>
              <q-select
                v-model="exportForm.status"
                :options="[
                  { label: 'Solo Cobros Pagados en Caja (PAID - Recomendado)', value: 'PAID' },
                  { label: 'Todos los Registros (Cobrados, Exentos, Pendientes)', value: 'ALL' }
                ]"
                emit-value
                map-options
                dense
                outlined
              />
            </div>
          </div>

          <div class="pt-4 flex justify-end space-x-2 border-t border-slate-100">
            <q-btn flat label="Cancelar" v-close-popup no-caps />
            <q-btn
              color="teal-8"
              class="bg-teal-700 text-white font-semibold"
              icon="download"
              label="Descargar Reporte (.xlsx)"
              no-caps
              :loading="downloadingExcel"
              @click="downloadAccountingExcel"
            />
          </div>
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
const clinicId = computed(() => user.value?.clinicId || user.value?.clinic_id || DEFAULT_CLINIC_ID)

const todayStr = new Date().toISOString().substring(0, 10)
const selectedDate = ref(todayStr)
const loading = ref(false)
const appointments = ref([])
const summary = ref({})
const clinicAnalytics = ref(null)

const showPaymentModal = ref(false)
const currentApp = ref(null)
const submittingPay = ref(false)

const showExportModal = ref(false)
const downloadingExcel = ref(false)
const exportForm = reactive({
  start_date: '',
  end_date: todayStr,
  status: 'PAID',
  bcv_rate: 65.50
})

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

function setDate (dateVal) {
  selectedDate.value = dateVal
  loadData()
}

async function loadData () {
  loading.value = true
  const id = clinicId.value
  try {
    const [appsResp, sumResp, analyticsResp] = await Promise.allSettled([
      api.get(`/appointments?clinic_id=${id}&date=${selectedDate.value}`),
      api.get(`/clinics/${id}/cashier/daily-summary?date=${selectedDate.value}`),
      api.get(`/clinics/${id}/analytics?days=30`)
    ])

    if (appsResp.status === 'fulfilled') {
      appointments.value = appsResp.value.data
    }
    if (sumResp.status === 'fulfilled') {
      summary.value = sumResp.value.data
    }
    if (analyticsResp.status === 'fulfilled') {
      clinicAnalytics.value = analyticsResp.value.data
    }
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
  const id = clinicId.value
  try {
    await api.post(`/clinics/${id}/payments/${currentApp.value.id}/record`, payForm)
    Notify.create({ type: 'positive', message: '¡Cobro registrado exitosamente en caja!' })
    showPaymentModal.value = false
    await loadData()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Error al procesar cobro.' })
  } finally {
    submittingPay.value = false
  }
}

function formatDate (isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
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
  return 'bg-amber-100 text-amber-800'
}

function openExportModal () {
  exportForm.start_date = ''
  exportForm.end_date = selectedDate.value || todayStr
  exportForm.status = 'PAID'
  exportForm.bcv_rate = 65.50
  showExportModal.value = true
}

function setExportPreset (type) {
  if (type === 'today') {
    exportForm.start_date = selectedDate.value || todayStr
    exportForm.end_date = selectedDate.value || todayStr
  } else if (type === '30days') {
    const d = new Date()
    d.setDate(d.getDate() - 30)
    exportForm.start_date = d.toISOString().substring(0, 10)
    exportForm.end_date = todayStr
  } else if (type === 'all') {
    exportForm.start_date = ''
    exportForm.end_date = ''
  }
}

async function downloadAccountingExcel () {
  downloadingExcel.value = true
  const id = clinicId.value
  try {
    let url = `/clinics/${id}/cashier/export-accounting-excel?bcv_rate=${exportForm.bcv_rate || 65.50}`
    if (exportForm.start_date) url += `&start_date=${exportForm.start_date}`
    if (exportForm.end_date) url += `&end_date=${exportForm.end_date}`
    if (exportForm.status && exportForm.status !== 'ALL') url += `&status=${exportForm.status}`

    const response = await api.get(url, { responseType: 'blob' })
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    const fileName = `Libro_Contable_${selectedDate.value || todayStr}.xlsx`
    link.setAttribute('download', fileName)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)

    Notify.create({
      type: 'positive',
      message: '¡Libro contable exportado exitosamente en formato Excel!'
    })
    showExportModal.value = false
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: 'Error al exportar el libro contable en Excel.'
    })
  } finally {
    downloadingExcel.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
