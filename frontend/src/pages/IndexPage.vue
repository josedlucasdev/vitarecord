<template>
  <q-page class="p-6 bg-slate-50 min-h-screen">
    <!-- Vista Especializada de Agenda y Calendario para Médicos -->
    <div v-if="userRole === 'DOCTOR'" class="max-w-7xl mx-auto">
      <DoctorCalendarDashboard />
    </div>

    <!-- Vista de Analítica & KPIs para Administradores, SuperAdmins y Personal Clínico -->
    <div v-else class="max-w-7xl mx-auto space-y-6">

      <!-- Barra Superior de Contexto y Filtros -->
      <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center space-x-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-100 text-teal-800 flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-teal-500 animate-pulse"></span>
              {{ userRole === 'SUPERADMIN' ? 'Auditoría Multi-Tenant • SuperAdmin' : 'Sede Operativa Local' }}
            </span>
            <span class="text-xs text-slate-400">Analítica & KPIs en Tiempo Real</span>
          </div>

          <h1 class="text-2xl font-black text-slate-900 mt-1 flex items-center gap-2">
            <q-icon name="analytics" class="text-teal-600" />
            <span>Dashboard Clínico: {{ currentClinicName }}</span>
          </h1>
          <p class="text-xs text-slate-500 mt-0.5">
            Métricas de atención médica, flujo de pacientes, facturación en caja y ocupación de consultorios.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <!-- Selector de Clínica para SUPERADMIN -->
          <div v-if="userRole === 'SUPERADMIN' && allClinics.length > 0" class="min-w-[240px]">
            <q-select
              v-model="selectedClinicId"
              :options="allClinics"
              option-value="id"
              option-label="name"
              emit-value
              map-options
              dense
              outlined
              label="Seleccionar Clínica"
              bg-color="white"
              @update:model-value="loadAnalytics"
            >
              <template v-slot:prepend>
                <q-icon name="apartment" color="teal" size="18px" />
              </template>
            </q-select>
          </div>

          <!-- Selector de Período -->
          <q-btn-toggle
            v-model="selectedDays"
            dense
            rounded
            toggle-color="teal-800"
            color="slate-100"
            text-color="slate-700"
            toggle-text-color="white"
            no-caps
            class="shadow-none border border-slate-200 text-xs font-medium"
            :options="[
              { label: '7D', value: 7 },
              { label: '30D', value: 30 },
              { label: '90D', value: 90 },
              { label: 'Todo', value: 0 }
            ]"
            @update:model-value="loadAnalytics"
          />

          <!-- Botón de Refrescar -->
          <q-btn
            flat
            round
            dense
            color="teal-800"
            icon="refresh"
            :loading="loading"
            @click="loadAnalytics"
          >
            <q-tooltip>Actualizar Métricas</q-tooltip>
          </q-btn>

          <!-- Botón Exportar Excel Contable -->
          <q-btn
            unelevated
            size="sm"
            color="teal-8"
            class="bg-teal-700 text-white font-semibold rounded-lg px-3 shadow-sm"
            icon="file_download"
            label="Exportar Excel Contable"
            no-caps
            to="/clinic/cashier"
          >
            <q-tooltip>Abrir asistente de exportación contable en Excel</q-tooltip>
          </q-btn>
        </div>
      </div>

      <!-- Estado de Carga -->
      <div v-if="loading && !analytics" class="text-center py-20 bg-white rounded-3xl border border-slate-200">
        <q-spinner-dots color="teal" size="50px" />
        <p class="text-slate-500 mt-3 text-sm font-medium">Calculando métricas y construyendo gráficos...</p>
      </div>

      <!-- Estado de Error / Sin Clínica Asignada -->
      <div v-else-if="errorMessage" class="p-8 bg-red-50 rounded-3xl border border-red-200 text-center">
        <q-icon name="warning" color="negative" size="48px" class="mb-3" />
        <h3 class="text-lg font-bold text-red-900">{{ errorMessage }}</h3>
        <p class="text-sm text-red-700 mt-1">Por favor verifica que la clínica esté activa y que tu usuario posea permisos asignados.</p>
      </div>

      <!-- Contenido Principal del Dashboard -->
      <template v-else-if="analytics">
        <!-- 1. Grid de 6 Tarjetas KPIs Principales -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
          <!-- KPI 1: Citas Totales -->
          <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col justify-between hover:shadow-md transition-shadow">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-400 uppercase">Citas Totales</span>
              <div class="w-8 h-8 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center">
                <q-icon name="calendar_month" size="18px" />
              </div>
            </div>
            <div class="mt-3">
              <div class="text-2xl font-extrabold text-slate-900">{{ analytics.kpis.total_appointments }}</div>
              <div class="text-2xs text-teal-600 font-semibold mt-1 flex items-center gap-1">
                <span>{{ analytics.kpis.confirmed_appointments }} confirmadas</span>
              </div>
            </div>
          </div>

          <!-- KPI 2: Total Recaudado -->
          <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col justify-between hover:shadow-md transition-shadow">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-400 uppercase">Recaudación</span>
              <div class="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
                <q-icon name="payments" size="18px" />
              </div>
            </div>
            <div class="mt-3">
              <div class="text-2xl font-extrabold text-emerald-700">${{ Number(analytics.kpis.total_revenue).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</div>
              <div class="text-2xs text-slate-500 mt-1">
                {{ analytics.kpis.total_paid_count }} cobros en caja
              </div>
            </div>
          </div>

          <!-- KPI 3: Tasa de Efectividad -->
          <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col justify-between hover:shadow-md transition-shadow">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-400 uppercase">Efectividad</span>
              <div class="w-8 h-8 rounded-xl bg-cyan-50 text-cyan-700 flex items-center justify-center">
                <q-icon name="task_alt" size="18px" />
              </div>
            </div>
            <div class="mt-3">
              <div class="text-2xl font-extrabold text-cyan-800">{{ analytics.kpis.attendance_rate_pct }}%</div>
              <div class="text-2xs text-slate-500 mt-1">
                Asistencia de turnos
              </div>
            </div>
          </div>

          <!-- KPI 4: Pacientes Únicos -->
          <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col justify-between hover:shadow-md transition-shadow">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-400 uppercase">Pacientes</span>
              <div class="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center">
                <q-icon name="groups" size="18px" />
              </div>
            </div>
            <div class="mt-3">
              <div class="text-2xl font-extrabold text-slate-900">{{ analytics.kpis.unique_patients }}</div>
              <div class="text-2xs text-slate-500 mt-1">
                Atendidos en la sede
              </div>
            </div>
          </div>

          <!-- KPI 5: Médicos Afiliados -->
          <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col justify-between hover:shadow-md transition-shadow">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-400 uppercase">Especialistas</span>
              <div class="w-8 h-8 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center">
                <q-icon name="medical_services" size="18px" />
              </div>
            </div>
            <div class="mt-3">
              <div class="text-2xl font-extrabold text-slate-900">{{ analytics.kpis.active_doctors }}</div>
              <div class="text-2xs text-purple-700 font-semibold mt-1">
                Plantilla activa
              </div>
            </div>
          </div>

          <!-- KPI 6: Consultorios Activos -->
          <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col justify-between hover:shadow-md transition-shadow">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-400 uppercase">Salas / Mutex</span>
              <div class="w-8 h-8 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center">
                <q-icon name="meeting_room" size="18px" />
              </div>
            </div>
            <div class="mt-3">
              <div class="text-2xl font-extrabold text-slate-900">{{ analytics.kpis.active_rooms }}</div>
              <div class="text-2xs text-amber-700 font-semibold mt-1">
                Espacios disponibles
              </div>
            </div>
          </div>
        </div>

        <!-- 2. Grid de Gráficos Analíticos -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

          <!-- Gráfico 1: Tendencia Temporal (Ocupa 2 columnas) -->
          <div class="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80">
            <div class="flex items-center justify-between mb-4">
              <div>
                <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
                  <q-icon name="show_chart" color="teal" size="20px" />
                  <span>Tendencia de Citas Médicas</span>
                </h3>
                <p class="text-xs text-slate-500">Evolución de citas confirmadas, completadas y canceladas por día.</p>
              </div>
              <span class="text-xs font-semibold px-2 py-1 rounded bg-slate-100 text-slate-600">
                {{ selectedDays === 0 ? 'Histórico' : `Últimos ${selectedDays} días` }}
              </span>
            </div>
            <div class="relative h-72 w-full">
              <canvas ref="trendCanvas"></canvas>
            </div>
          </div>

          <!-- Gráfico 2: Distribución de Estados de Citas (Doughnut) -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80">
            <div class="mb-4">
              <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
                <q-icon name="pie_chart" color="teal" size="20px" />
                <span>Estados de Citas</span>
              </h3>
              <p class="text-xs text-slate-500">Distribución porcentual del volumen de consultas.</p>
            </div>
            <div class="relative h-60 w-full flex items-center justify-center">
              <canvas ref="statusCanvas"></canvas>
            </div>
            <!-- Leyenda Detallada -->
            <div class="mt-4 space-y-1.5 max-h-32 overflow-y-auto pr-1">
              <div
                v-for="st in analytics.status_distribution.slice(0, 5)"
                :key="st.status"
                class="flex items-center justify-between text-xs text-slate-600"
              >
                <span class="flex items-center gap-1.5 truncate">
                  <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: st.color }"></span>
                  <span class="truncate">{{ st.label }}</span>
                </span>
                <span class="font-bold text-slate-800">{{ st.count }} ({{ st.percentage }}%)</span>
              </div>
            </div>
          </div>

          <!-- Gráfico 3: Demanda por Especialidad Médica -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80">
            <div class="mb-4">
              <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
                <q-icon name="medical_information" color="indigo" size="20px" />
                <span>Especialidades Más Solicitadas</span>
              </h3>
              <p class="text-xs text-slate-500">Volumen de citas según área médica.</p>
            </div>
            <div class="relative h-64 w-full">
              <canvas ref="specialtyCanvas"></canvas>
            </div>
          </div>

          <!-- Gráfico 4: Recaudación por Método de Pago -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80">
            <div class="mb-4">
              <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
                <q-icon name="point_of_sale" color="emerald" size="20px" />
                <span>Ingresos por Método de Pago</span>
              </h3>
              <p class="text-xs text-slate-500">Cobros liquidados en caja ($ USD).</p>
            </div>
            <div class="relative h-60 w-full flex items-center justify-center">
              <canvas ref="paymentCanvas"></canvas>
            </div>
            <div class="mt-4 space-y-1.5">
              <div
                v-for="pm in analytics.payment_methods"
                :key="pm.method"
                class="flex items-center justify-between text-xs text-slate-600"
              >
                <span class="flex items-center gap-1.5">
                  <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: pm.color }"></span>
                  <span>{{ pm.label }}</span>
                </span>
                <span class="font-bold text-emerald-800">${{ Number(pm.amount).toFixed(2) }} ({{ pm.count }})</span>
              </div>
            </div>
          </div>

          <!-- Gráfico 5: Ocupación de Consultorios y Salas -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80">
            <div class="mb-4">
              <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
                <q-icon name="meeting_room" color="amber" size="20px" />
                <span>Ocupación de Consultorios</span>
              </h3>
              <p class="text-xs text-slate-500">Citas asignadas por espacio físico.</p>
            </div>
            <div class="relative h-64 w-full">
              <canvas ref="roomCanvas"></canvas>
            </div>
          </div>
        </div>

        <!-- 3. Tabla de Citas Recientes / del Día -->
        <div class="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden">
          <div class="p-5 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
                <q-icon name="history" color="teal" size="20px" />
                <span>Citas Recientes y Próximas de la Sede</span>
              </h3>
              <p class="text-xs text-slate-500">Últimos turnos agendados en esta clínica.</p>
            </div>
            <q-btn
              flat
              dense
              no-caps
              color="teal-800"
              label="Ver Todas en Gestión de Citas"
              icon-right="chevron_right"
              to="/appointments/my-list"
              class="font-semibold text-xs"
            />
          </div>

          <div v-if="analytics.today_appointments.length === 0" class="text-center py-10 text-slate-400 text-sm">
            No se registran citas recientes en este período para la sede.
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-700">
              <thead class="bg-slate-50 text-slate-400 uppercase text-2xs font-bold border-b border-slate-100">
                <tr>
                  <th class="p-3.5">Fecha y Hora</th>
                  <th class="p-3.5">Paciente</th>
                  <th class="p-3.5">Médico Especialista</th>
                  <th class="p-3.5">Consultorio</th>
                  <th class="p-3.5">Estado Cita</th>
                  <th class="p-3.5">Caja / Pago</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="appt in analytics.today_appointments" :key="appt.id" class="hover:bg-slate-50/60 transition-colors">
                  <td class="p-3.5 font-semibold text-slate-900">{{ appt.start_time }}</td>
                  <td class="p-3.5 font-medium text-slate-800">{{ appt.patient_name }}</td>
                  <td class="p-3.5">
                    <div class="font-medium text-slate-900">{{ appt.doctor_name }}</div>
                    <div class="text-2xs text-slate-400">{{ appt.specialty || 'Especialista' }}</div>
                  </td>
                  <td class="p-3.5">
                    <span class="px-2 py-0.5 rounded bg-slate-100 font-mono text-2xs text-slate-700">
                      {{ appt.room_name }}
                    </span>
                  </td>
                  <td class="p-3.5">
                    <span
                      class="px-2 py-0.5 rounded-full text-2xs font-bold"
                      :class="getStatusBadgeClass(appt.status)"
                    >
                      {{ formatStatus(appt.status) }}
                    </span>
                  </td>
                  <td class="p-3.5">
                    <span
                      class="px-2 py-0.5 rounded text-2xs font-semibold"
                      :class="appt.payment_status === 'PAID' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'"
                    >
                      {{ appt.payment_status === 'PAID' ? 'PAGADO' : 'PENDIENTE' }}
                      {{ appt.amount ? `($${appt.amount})` : '' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </template>

    </div>
  </q-page>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import Chart from 'chart.js/auto'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'
import DoctorCalendarDashboard from 'src/components/doctor/DoctorCalendarDashboard.vue'

const { user, userRole, hasRole } = useAcl()

const loading = ref(false)
const errorMessage = ref('')
const allClinics = ref([])
const selectedClinicId = ref('')
const selectedDays = ref(30)
const analytics = ref(null)

// Referencias a los canvas de Chart.js
const trendCanvas = ref(null)
const statusCanvas = ref(null)
const specialtyCanvas = ref(null)
const paymentCanvas = ref(null)
const roomCanvas = ref(null)

// Instancias de Chart.js para destrucción y recreación limpia
let trendChartInstance = null
let statusChartInstance = null
let specialtyChartInstance = null
let paymentChartInstance = null
let roomChartInstance = null

const currentClinicName = computed(() => {
  if (analytics.value) {
    return analytics.value.clinic_name
  }
  const match = allClinics.value.find(c => c.id === selectedClinicId.value)
  return match ? match.name : 'Sede Principal'
})

function destroyAllCharts () {
  if (trendChartInstance) { trendChartInstance.destroy(); trendChartInstance = null }
  if (statusChartInstance) { statusChartInstance.destroy(); statusChartInstance = null }
  if (specialtyChartInstance) { specialtyChartInstance.destroy(); specialtyChartInstance = null }
  if (paymentChartInstance) { paymentChartInstance.destroy(); paymentChartInstance = null }
  if (roomChartInstance) { roomChartInstance.destroy(); roomChartInstance = null }
}

async function loadClinicsList () {
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.get('/clinics', {
      headers: { Authorization: `Bearer ${token}` }
    })
    allClinics.value = data
    if (data.length > 0 && !selectedClinicId.value) {
      // Si el usuario pertenece a una clínica, preseleccionar la suya
      if (user.value?.clinic_id) {
        selectedClinicId.value = user.value.clinic_id
      } else {
        selectedClinicId.value = data[0].id
      }
    }
  } catch (err) {
    console.error('Error al consultar lista de clínicas:', err)
  }
}

async function loadAnalytics () {
  loading.value = true
  errorMessage.value = ''
  destroyAllCharts()

  try {
    const token = localStorage.getItem('access_token')
    let clinicToQuery = selectedClinicId.value

    // Si no es SuperAdmin, forzar la clínica del usuario
    if (userRole.value !== 'SUPERADMIN' && user.value?.clinic_id) {
      clinicToQuery = user.value.clinic_id
    }

    if (!clinicToQuery) {
      errorMessage.value = 'No se ha seleccionado ninguna sede clínica.'
      loading.value = false
      return
    }

    const { data } = await api.get(`/clinics/${clinicToQuery}/analytics`, {
      params: { days: selectedDays.value },
      headers: { Authorization: `Bearer ${token}` }
    })

    analytics.value = data
    selectedClinicId.value = data.clinic_id

    // Renderizar los gráficos tras la actualización del DOM
    await nextTick()
    renderCharts(data)
  } catch (err) {
    console.error('Error al cargar analíticas:', err)
    errorMessage.value = err.response?.data?.detail || 'No se pudieron consultar las analíticas de la sede.'
  } finally {
    loading.value = false
  }
}

function renderCharts (data) {
  destroyAllCharts()

  // 1. Tendencia Temporal (Line Chart)
  if (trendCanvas.value && data.trends && data.trends.length > 0) {
    trendChartInstance = new Chart(trendCanvas.value, {
      type: 'line',
      data: {
        labels: data.trends.map(t => t.date),
        datasets: [
          {
            label: 'Confirmadas',
            data: data.trends.map(t => t.confirmed),
            borderColor: '#0d9488',
            backgroundColor: 'rgba(13, 148, 136, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5
          },
          {
            label: 'Completadas',
            data: data.trends.map(t => t.completed),
            borderColor: '#10b981',
            backgroundColor: 'transparent',
            borderDash: [4, 4],
            tension: 0.35,
            borderWidth: 2
          },
          {
            label: 'Canceladas / No Show',
            data: data.trends.map(t => t.cancelled),
            borderColor: '#ef4444',
            backgroundColor: 'transparent',
            tension: 0.35,
            borderWidth: 1.5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { font: { size: 11, family: 'Inter, sans-serif' } } }
        },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } }
        }
      }
    })
  }

  // 2. Distribución de Estados (Doughnut Chart)
  if (statusCanvas.value && data.status_distribution && data.status_distribution.length > 0) {
    statusChartInstance = new Chart(statusCanvas.value, {
      type: 'doughnut',
      data: {
        labels: data.status_distribution.map(s => s.label),
        datasets: [{
          data: data.status_distribution.map(s => s.count),
          backgroundColor: data.status_distribution.map(s => s.color),
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: { display: false }
        }
      }
    })
  }

  // 3. Especialidades Más Solicitadas (Horizontal Bar)
  if (specialtyCanvas.value && data.specialties && data.specialties.length > 0) {
    specialtyChartInstance = new Chart(specialtyCanvas.value, {
      type: 'bar',
      data: {
        labels: data.specialties.map(s => s.specialty),
        datasets: [{
          label: 'Citas',
          data: data.specialties.map(s => s.count),
          backgroundColor: '#6366f1',
          borderRadius: 8
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: '#f1f5f9' } },
          y: { grid: { display: false }, ticks: { font: { size: 11 } } }
        }
      }
    })
  }

  // 4. Métodos de Pago (Doughnut Chart)
  if (paymentCanvas.value && data.payment_methods && data.payment_methods.length > 0) {
    paymentChartInstance = new Chart(paymentCanvas.value, {
      type: 'doughnut',
      data: {
        labels: data.payment_methods.map(p => p.label),
        datasets: [{
          data: data.payment_methods.map(p => Number(p.amount)),
          backgroundColor: data.payment_methods.map(p => p.color),
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return `${ctx.label}: $${Number(ctx.raw).toFixed(2)} USD`
              }
            }
          }
        }
      }
    })
  }

  // 5. Ocupación de Consultorios (Bar Chart)
  if (roomCanvas.value && data.room_utilization && data.room_utilization.length > 0) {
    roomChartInstance = new Chart(roomCanvas.value, {
      type: 'bar',
      data: {
        labels: data.room_utilization.map(r => r.room_name),
        datasets: [{
          label: 'Citas Asignadas',
          data: data.room_utilization.map(r => r.appointments_count),
          backgroundColor: '#f59e0b',
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } }
        }
      }
    })
  }
}

function formatStatus (status) {
  const map = {
    CONFIRMED: 'Confirmada',
    COMPLETED: 'Completada',
    PENDING_DOCTOR_APPROVAL: 'Aprobación Médica',
    PENDING_PATIENT_ACCEPTANCE: 'Aceptación Paciente',
    SCHEDULED: 'Agendada',
    CANCELLED_BY_PATIENT: 'Cancelada (Paciente)',
    CANCELLED_BY_DOCTOR: 'Cancelada (Médico)',
    CANCELLED_BY_CLINIC: 'Cancelada (Clínica)',
    REJECTED_BY_PATIENT: 'Rechazada (Paciente)',
    REJECTED_BY_DOCTOR: 'Rechazada (Médico)',
    NO_SHOW: 'No Asistió',
    RESCHEDULED: 'Reagendada'
  }
  return map[status] || status
}

function getStatusBadgeClass (status) {
  if (status === 'COMPLETED' || status === 'CONFIRMED') {
    return 'bg-emerald-100 text-emerald-800'
  }
  if (status.includes('PENDING')) {
    return 'bg-amber-100 text-amber-800'
  }
  if (status.includes('CANCELLED') || status.includes('REJECTED') || status === 'NO_SHOW') {
    return 'bg-red-100 text-red-800'
  }
  return 'bg-blue-100 text-blue-800'
}

onMounted(async () => {
  if (userRole.value !== 'DOCTOR') {
    await loadClinicsList()
    await loadAnalytics()
  }
})

onUnmounted(() => {
  destroyAllCharts()
})
</script>
