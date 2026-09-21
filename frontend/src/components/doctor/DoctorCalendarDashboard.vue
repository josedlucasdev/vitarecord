<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Header Banner del Médico (Optimizado para Móvil, Tablet y Desktop) -->
    <div class="bg-white p-4 sm:p-6 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center space-x-2">
          <span class="px-2.5 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs font-bold bg-teal-100/80 text-teal-800 flex items-center gap-1.5 border border-teal-200">
            <span class="w-2 h-2 rounded-full bg-teal-600 animate-pulse"></span>
            {{ doctorSpecialty }}
          </span>
          <span class="text-xs font-medium text-slate-400 hidden sm:inline">Panel Médico & Agenda</span>
        </div>

        <h1 class="text-xl sm:text-2xl lg:text-3xl font-black text-slate-900 mt-1.5 flex items-center gap-2">
          <q-icon name="medical_services" class="text-[#24796a]" size="24px" />
          <span class="truncate">{{ doctorDisplayName }}</span>
        </h1>

        <p class="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-1.5 sm:gap-2">
          <span class="font-medium text-slate-600 capitalize flex items-center gap-1">
            <q-icon name="today" size="14px" class="text-slate-400" />
            {{ todayFormattedText }}
          </span>
          <span v-if="clinicDisplayName" class="text-slate-300">•</span>
          <span v-if="clinicDisplayName" class="font-semibold text-teal-800 flex items-center gap-1 bg-teal-50 px-2 py-0.5 rounded-md border border-teal-100 truncate">
            <q-icon name="apartment" size="14px" class="text-[#24796a] shrink-0" />
            <span class="truncate">{{ clinicDisplayName }}</span>
          </span>
        </p>
      </div>

      <!-- Botones de Acción Superior (Flex-1 en móvil para pulsar con el pulgar) -->
      <div class="flex items-center gap-2 w-full md:w-auto">
        <!-- Botón Configurar Horarios -->
        <q-btn
          outline
          color="teal-8"
          icon="event_note"
          label="Horarios"
          no-caps
          to="/doctor/schedule"
          class="flex-1 md:flex-none font-semibold text-xs rounded-xl py-2 px-3 min-h-[40px]"
        >
          <q-tooltip>Gestionar turnos semanales y disponibilidad</q-tooltip>
        </q-btn>

        <!-- Botón Refrescar Agenda -->
        <q-btn
          unelevated
          color="teal-8"
          icon="refresh"
          label="Actualizar"
          no-caps
          :loading="loading"
          @click="fetchAppointments"
          class="flex-1 md:flex-none font-bold text-xs rounded-xl py-2 px-3.5 shadow-sm bg-[#24796a] text-white min-h-[40px]"
        />
      </div>
    </div>

    <!-- Barra de Métricas y Filtros Rápidos (KPI Cards interactivos adaptados) -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 sm:gap-3.5">
      <!-- Citas Hoy -->
      <div
        @click="selectTab('today')"
        class="cursor-pointer p-3 sm:p-4 rounded-2xl border transition-all duration-200 touch-manipulation active:scale-[0.98]"
        :class="activeTab === 'today' && !selectedCalendarDate ? 'bg-teal-50/90 border-[#24796a] shadow-sm ring-2 ring-[#24796a]/20' : 'bg-white border-slate-200/90 hover:border-teal-300 hover:shadow-xs'"
      >
        <div class="flex items-center justify-between">
          <span class="text-2xs sm:text-xs font-bold text-slate-600 uppercase tracking-wider">Citas Hoy</span>
          <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-teal-100 text-[#24796a] flex items-center justify-center shrink-0">
            <q-icon name="today" size="16px" />
          </div>
        </div>
        <div class="mt-1.5 sm:mt-2 text-xl sm:text-2xl lg:text-3xl font-black text-slate-900">{{ countToday }}</div>
        <div class="text-3xs sm:text-2xs text-slate-500 mt-0.5 truncate">Programadas hoy</div>
      </div>

      <!-- Próximas Citas (Futuras) -->
      <div
        @click="selectTab('future')"
        class="cursor-pointer p-3 sm:p-4 rounded-2xl border transition-all duration-200 touch-manipulation active:scale-[0.98]"
        :class="activeTab === 'future' && !selectedCalendarDate ? 'bg-indigo-50/80 border-indigo-600 shadow-sm ring-2 ring-indigo-500/20' : 'bg-white border-slate-200/90 hover:border-indigo-300 hover:shadow-xs'"
      >
        <div class="flex items-center justify-between">
          <span class="text-2xs sm:text-xs font-bold text-slate-600 uppercase tracking-wider">Próximas</span>
          <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
            <q-icon name="date_range" size="18px" />
          </div>
        </div>
        <div class="mt-1.5 sm:mt-2 text-xl sm:text-2xl lg:text-3xl font-black text-slate-900">{{ countFuture }}</div>
        <div class="text-3xs sm:text-2xs text-slate-500 mt-0.5 truncate">Días posteriores</div>
      </div>

      <!-- Pendientes de Aprobación -->
      <div
        @click="selectTab('pending')"
        class="cursor-pointer p-3 sm:p-4 rounded-2xl border transition-all duration-200 touch-manipulation active:scale-[0.98]"
        :class="activeTab === 'pending' && !selectedCalendarDate ? 'bg-amber-50 border-amber-500 shadow-sm ring-2 ring-amber-500/20' : 'bg-white border-slate-200/90 hover:border-amber-300 hover:shadow-xs'"
      >
        <div class="flex items-center justify-between">
          <span class="text-2xs sm:text-xs font-bold text-slate-600 uppercase tracking-wider">Por Aprobar</span>
          <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center shrink-0">
            <q-icon name="hourglass_top" size="18px" />
          </div>
        </div>
        <div class="mt-1.5 sm:mt-2 text-xl sm:text-2xl lg:text-3xl font-black text-amber-600">{{ countPending }}</div>
        <div class="text-3xs sm:text-2xs text-slate-500 mt-0.5 truncate">Por confirmar</div>
      </div>

      <!-- Historial Pasadas -->
      <div
        @click="selectTab('past')"
        class="cursor-pointer p-3 sm:p-4 rounded-2xl border transition-all duration-200 touch-manipulation active:scale-[0.98]"
        :class="activeTab === 'past' && !selectedCalendarDate ? 'bg-slate-100 border-slate-500 shadow-sm ring-2 ring-slate-400/20' : 'bg-white border-slate-200/90 hover:border-slate-400 hover:shadow-xs'"
      >
        <div class="flex items-center justify-between">
          <span class="text-2xs sm:text-xs font-bold text-slate-600 uppercase tracking-wider">Pasadas</span>
          <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center shrink-0">
            <q-icon name="history" size="16px" />
          </div>
        </div>
        <div class="mt-1.5 sm:mt-2 text-xl sm:text-2xl lg:text-3xl font-black text-slate-900">{{ countPast }}</div>
        <div class="text-3xs sm:text-2xs text-slate-500 mt-0.5 truncate">Concluidas</div>
      </div>

      <!-- Total Histórico (ocupa 2 columnas en móvil para alineación limpia) -->
      <div
        @click="selectTab('all')"
        class="col-span-2 sm:col-span-1 cursor-pointer p-3 sm:p-4 rounded-2xl border transition-all duration-200 touch-manipulation active:scale-[0.98]"
        :class="activeTab === 'all' && !selectedCalendarDate ? 'bg-teal-50/90 border-[#24796a] shadow-sm ring-2 ring-[#24796a]/20' : 'bg-white border-slate-200/90 hover:border-teal-300 hover:shadow-xs'"
      >
        <div class="flex items-center justify-between">
          <span class="text-2xs sm:text-xs font-bold text-slate-600 uppercase tracking-wider">Total Citas</span>
          <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0">
            <q-icon name="view_agenda" size="16px" />
          </div>
        </div>
        <div class="mt-1.5 sm:mt-2 text-xl sm:text-2xl lg:text-3xl font-black text-slate-900">{{ appointments.length }}</div>
        <div class="text-3xs sm:text-2xs text-slate-500 mt-0.5 truncate">Historial total</div>
      </div>
    </div>

    <!-- Estructura Principal: Calendario Siempre Visible a la Izquierda + Agenda a la Derecha -->
    <div class="grid grid-cols-1 md:grid-cols-12 gap-5 sm:gap-6 items-start">
      
      <!-- Columna Izquierda: Calendario q-date Minimal Permanente (Siempre Visible) -->
      <div class="md:col-span-5 lg:col-span-4 space-y-4">
        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
          
          <!-- Cabecera Personalizada del Calendario -->
          <div class="p-3.5 sm:p-4 bg-white border-b [border-bottom-style:dashed] border-slate-200/80 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-lg bg-teal-100 text-[#24796a] flex items-center justify-center">
                <q-icon name="calendar_month" size="16px" />
              </div>
              <div class="flex flex-col justify-center">
                <div class="text-xs sm:text-sm font-bold text-slate-900 leading-none m-0 p-0">Calendario Mensual</div>
                <div class="text-3xs sm:text-2xs text-slate-500 leading-none m-0 p-0 mt-0.5">Toca un día para filtrar</div>
              </div>
            </div>

            <!-- Botón Limpiar si hay fecha seleccionada -->
            <q-btn
              v-if="selectedCalendarDate"
              flat
              dense
              size="xs"
              color="negative"
              icon="cancel"
              label="Quitar fecha"
              no-caps
              @click="clearDateFilter"
              class="font-semibold text-2xs"
            />
          </div>

          <!-- Componente q-date con 'minimal' -->
          <div class="p-1 sm:p-2 flex justify-center">
            <q-date
              v-model="selectedCalendarDate"
              :events="appointmentDateEvents"
              :event-color="() => 'teal-8'"
              color="teal-8"
              text-color="white"
              mask="YYYY/MM/DD"
              today-btn
              flat
              minimal
              class="w-full border-0 shadow-none font-sans"
              @update:model-value="onDateSelect"
            />
          </div>

          <!-- Pie del Calendario con Leyenda y Botón Ir a Hoy -->
          <div class="px-3.5 sm:px-4 py-2.5 sm:py-3 bg-slate-50/70 border-t border-slate-100 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-[#24796a] inline-block"></span>
              <span class="text-sm font-bold text-slate-800">Días con citas</span>
            </div>
            <div class="flex items-center gap-1.5">
              <q-btn
                flat
                dense
                size="md"
                color="teal-8"
                label="Ir a Hoy"
                icon="today"
                no-caps
                @click="jumpToToday"
                class="font-extrabold text-sm bg-teal-50 px-3 py-1 rounded-lg text-[#24796a]"
              />
            </div>
          </div>
        </div>

        <!-- Tarjeta Informativa de Resumen Diario -->
        <div v-if="selectedCalendarDate" class="bg-teal-50/70 border border-teal-200/80 rounded-2xl p-3.5 sm:p-4 shadow-xs">
          <div class="flex items-center gap-2 text-xs font-bold text-teal-900">
            <q-icon name="event_note" size="18px" class="text-[#24796a]" />
            <span>Filtro de Día Activo</span>
          </div>
          <p class="text-xs sm:text-sm font-extrabold text-slate-800 mt-1 capitalize">
            {{ formatCalendarDateDisplay(selectedCalendarDate) }}
          </p>
          <div class="mt-2 text-xs text-slate-600 flex items-center justify-between">
            <span>Citas en esta fecha:</span>
            <span class="font-black text-teal-900 px-2 py-0.5 bg-teal-100 rounded-full text-xs">
              {{ filteredAppointments.length }}
            </span>
          </div>
        </div>

      </div>

      <!-- Columna Derecha: Barra de Herramientas, Filtros y Lista de Citas (8 columnas en lg, 7 en md) -->
      <div class="md:col-span-7 lg:col-span-8 space-y-4">

        <!-- Filtros Integrados: Buscador + Selector de Estado (Apilado limpio en móvil) -->
        <div class="bg-white p-3.5 rounded-2xl border border-slate-200/80 shadow-sm grid grid-cols-1 sm:grid-cols-12 gap-2.5 sm:gap-3">
          <!-- Input de Búsqueda -->
          <div class="sm:col-span-7">
            <q-input
              v-model="searchQuery"
              dense
              outlined
              clearable
              placeholder="Buscar paciente, teléfono, motivo..."
              bg-color="slate-50"
              class="text-xs"
            >
              <template v-slot:prepend>
                <q-icon name="search" size="18px" color="teal-8" />
              </template>
            </q-input>
          </div>

          <!-- Selector de Estado -->
          <div class="sm:col-span-5">
            <q-select
              v-model="selectedStatusFilter"
              :options="statusFilterOptions"
              dense
              outlined
              emit-value
              map-options
              bg-color="slate-50"
              class="text-xs"
            >
              <template v-slot:prepend>
                <q-icon name="filter_list" size="18px" color="teal-8" />
              </template>
            </q-select>
          </div>
        </div>

        <!-- Aviso si hay filtro de fecha activo -->
        <div
          v-if="selectedCalendarDate"
          class="bg-teal-50 border border-teal-200 text-teal-950 px-3.5 sm:px-4 py-2.5 rounded-xl flex items-center justify-between text-xs shadow-xs"
        >
          <div class="flex items-center gap-2 truncate">
            <q-icon name="event_available" color="teal-8" size="18px" class="shrink-0" />
            <span class="truncate">Citas del <strong class="capitalize">{{ formatCalendarDateDisplay(selectedCalendarDate) }}</strong></span>
          </div>
          <q-btn
            flat
            dense
            size="xs"
            color="teal-9"
            label="Ver todas"
            no-caps
            @click="clearDateFilter"
            class="font-bold underline text-xs shrink-0 ml-2"
          />
        </div>

        <!-- Estado de Carga -->
        <div v-if="loading" class="bg-white p-10 sm:p-12 rounded-2xl border border-slate-200 text-center space-y-3">
          <q-spinner-dots color="teal" size="38px" />
          <p class="text-xs text-slate-500 font-medium">Consultando agenda médica en tiempo real...</p>
        </div>

        <!-- Estado Vacío -->
        <div
          v-else-if="filteredAppointments.length === 0"
          class="bg-white p-8 sm:p-12 rounded-2xl border border-slate-200 text-center space-y-4 shadow-sm"
        >
          <div class="w-14 h-14 sm:w-16 sm:h-16 mx-auto rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400">
            <q-icon name="event_busy" size="30px" />
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-800">No hay citas para mostrar</h3>
            <p class="text-xs text-slate-500 max-w-md mx-auto mt-1">
              {{ emptyMessage }}
            </p>
          </div>
          <div class="flex flex-wrap items-center justify-center gap-2 pt-2">
            <q-btn
              v-if="selectedCalendarDate || activeTab !== 'all' || searchQuery || selectedStatusFilter"
              outline
              color="teal-8"
              label="Restablecer Filtros"
              icon="restart_alt"
              no-caps
              size="sm"
              class="font-semibold rounded-xl min-h-[38px]"
              @click="resetAllFilters"
            />
            <q-btn
              color="teal-8"
              label="Ver Próximas Citas"
              icon="date_range"
              no-caps
              size="sm"
              class="font-bold rounded-xl shadow-xs bg-[#24796a] min-h-[38px]"
              @click="selectTab('future')"
            />
          </div>
        </div>

        <!-- Lista de Citas Médicas (Totalmente Responsive) -->
        <div v-else class="space-y-3 sm:space-y-3.5">
          <div
            v-for="app in paginatedAppointments"
            :key="app.id"
            class="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col md:flex-row items-stretch"
          >
            <!-- Franja Izquierda: Hora y Duración (En móvil se muestra como barra superior) -->
            <div class="bg-slate-50/90 px-4 py-2.5 md:py-3.5 md:w-36 flex md:flex-col items-center justify-between md:justify-center text-center md:gap-1.5 border-b md:border-b-0 md:border-r md:[border-right-style:dashed] border-slate-200/70 shrink-0 bg-white">
              <div class="flex md:flex-col items-center justify-center gap-1 md:gap-0 leading-none">
                <span class="text-xs font-extrabold text-slate-900 leading-none">
                  {{ formatTime(app.start_time) }}
                </span>
                <span class="text-3xs text-slate-400 leading-none my-0">-</span>
                <span class="text-xs font-semibold text-slate-700 leading-none">
                  {{ formatTime(app.end_time) }}
                </span>
              </div>
              <div class="px-2 py-0.5 bg-teal-100/70 text-teal-800 text-3xs font-black rounded-md uppercase tracking-wider">
                {{ calculateDuration(app.start_time, app.end_time) }}
              </div>
            </div>

            <!-- Cuerpo Central: Información del Paciente y Cita -->
            <div class="p-3.5 sm:p-4 flex-1 space-y-2">
              
              <!-- Badges de Estado y Ubicación -->
              <div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <!-- Estado Clínico -->
                <span
                  :class="statusBadgeClass(app.status)"
                  class="px-2 sm:px-2.5 py-0.5 rounded-full text-3xs sm:text-2xs font-bold uppercase tracking-wider flex items-center gap-1.5"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="statusDotClass(app.status)"></span>
                  {{ formatStatus(app.status) }}
                </span>

                <!-- Estado de Pago -->
                <span
                  :class="paymentBadgeClass(app.payment_status)"
                  class="px-2 sm:px-2.5 py-0.5 rounded-full text-3xs sm:text-2xs font-semibold"
                >
                  {{ app.payment_status === 'PAID' ? 'PAGADO' : 'PENDIENTE' }} • ${{ app.payment_amount || '0.00' }} {{ app.currency || 'USD' }}
                </span>

                <!-- Consultorio -->
                <span v-if="app.room_name" class="px-2 py-0.5 rounded-full text-3xs sm:text-2xs font-medium bg-slate-100 text-slate-700 flex items-center gap-1">
                  <q-icon name="meeting_room" size="12px" class="text-[#24796a]" />
                  {{ app.room_name }}
                </span>

                <!-- Sede / Clínica -->
                <span v-if="app.clinic_name" class="px-2 py-0.5 rounded-full text-3xs sm:text-2xs font-medium bg-slate-100 text-slate-600 flex items-center gap-1 hidden sm:flex">
                  <q-icon name="apartment" size="12px" class="text-slate-400" />
                  {{ app.clinic_name }}
                </span>
              </div>

              <!-- Nombre del Paciente y Motivo -->
              <div>
                <div class="flex items-center gap-2">
                  <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-teal-100 text-[#24796a] font-black text-xs flex items-center justify-center shrink-0 border border-teal-200">
                    {{ getPatientInitial(app.patient_name || app.patient_email) }}
                  </div>
                  <div>
                    <h3 class="font-extrabold text-slate-900 text-sm sm:text-base leading-tight flex items-center gap-1.5">
                      <span>{{ getPatientDisplayName(app) }}</span>
                      <span v-if="app.dependent_id" class="text-3xs px-1.5 py-0.2 bg-teal-50 text-teal-800 font-bold rounded border border-teal-200">
                        Familiar
                      </span>
                    </h3>
                  </div>
                </div>

                <p v-if="app.reason" class="text-xs text-slate-600 mt-1 italic pl-0 sm:pl-9">
                  "{{ app.reason }}"
                </p>
              </div>

              <!-- Metadatos de Contacto (con enlaces directos para móvil: tel y mail) -->
              <div class="text-xs text-slate-500 flex flex-wrap items-center gap-y-1 gap-x-3 sm:gap-x-4 pl-0 sm:pl-9">
                <!-- Fecha -->
                <span class="flex items-center gap-1 font-semibold text-slate-700">
                  <q-icon name="today" size="14px" class="text-[#24796a]" />
                  {{ formatDateDisplay(app.start_time) }}
                </span>
                
                <!-- Teléfono (enlace nativo tel: para llamar en móvil/tablet) -->
                <a
                  v-if="app.patient_phone"
                  :href="'tel:' + app.patient_phone"
                  class="flex items-center gap-1 text-teal-800 font-semibold hover:underline"
                >
                  <q-icon name="phone" size="14px" class="text-teal-600" />
                  <span>{{ app.patient_phone }}</span>
                </a>

                <!-- Correo (enlace nativo mailto:) -->
                <a
                  v-if="app.patient_email"
                  :href="'mailto:' + app.patient_email"
                  class="flex items-center gap-1 text-slate-500 hover:underline truncate max-w-[190px] sm:max-w-xs"
                >
                  <q-icon name="mail" size="14px" class="text-slate-400" />
                  <span class="truncate">{{ app.patient_email }}</span>
                </a>
              </div>
            </div>

            <!-- Columna Derecha: Acciones Médicas (Touch-friendly para móvil y tablet) -->
            <div class="p-3 sm:p-4 bg-white md:w-52 flex flex-col sm:flex-row md:flex-col justify-center items-center gap-2 shrink-0 border-t md:border-t-0 md:border-l border-slate-200/70">
              
              <!-- Botón Ficha de Triage si existen datos -->
              <q-btn
                v-if="app.intake_data && Object.keys(app.intake_data).length > 0"
                flat
                dense
                color="teal-8"
                icon="monitor_heart"
                label="Ficha de Triage"
                no-caps
                class="w-full text-xs font-semibold bg-teal-50 text-teal-900 rounded-xl hover:bg-teal-100 min-h-[38px]"
                @click="openTriageModal(app)"
              >
                <q-tooltip>Consultar signos vitales, alergias y antecedentes</q-tooltip>
              </q-btn>

              <!-- Si la cita está PENDING_DOCTOR_APPROVAL -> Aceptar / Rechazar -->
              <template v-if="app.status === 'PENDING_DOCTOR_APPROVAL'">
                <q-btn
                  unelevated
                  color="teal-8"
                  icon="check_circle"
                  label="Aceptar Cita"
                  no-caps
                  dense
                  class="w-full text-xs font-bold shadow-xs rounded-xl bg-[#24796a] text-white min-h-[40px]"
                  :loading="processingAcceptId === app.id"
                  @click="doctorAcceptApp(app.id)"
                >
                  <q-tooltip>Aprobar cita y notificar al paciente</q-tooltip>
                </q-btn>
                <q-btn
                  color="negative"
                  outline
                  icon="cancel"
                  label="Rechazar"
                  no-caps
                  dense
                  class="w-full text-xs font-semibold rounded-xl min-h-[36px]"
                  @click="promptDoctorReject(app.id)"
                />
              </template>

              <!-- Si está en estado activo de atención (CONFIRMED, SCHEDULED, CHECKED_IN, IN_CONSULTATION) -->
              <q-btn
                v-else-if="['CONFIRMED', 'SCHEDULED', 'CHECKED_IN', 'IN_CONSULTATION'].includes(app.status)"
                unelevated
                color="teal-8"
                icon="stethoscope"
                label="Atender Paciente"
                no-caps
                dense
                class="w-full text-xs font-bold shadow-xs rounded-xl bg-[#24796a] text-white min-h-[42px] touch-manipulation active:scale-[0.98]"
                :to="`/medical/consultation?appointment_id=${app.id}`"
              >
                <q-tooltip>Iniciar consulta médica, notas clínicas y recetas</q-tooltip>
              </q-btn>

              <!-- Si ya está COMPLETED -> Ver Consulta / Historia -->
              <q-btn
                v-else-if="app.status === 'COMPLETED'"
                outline
                color="teal-8"
                icon="history_edu"
                label="Ver Historia"
                no-caps
                dense
                class="w-full text-xs font-semibold rounded-xl min-h-[38px]"
                :to="`/medical/consultation?appointment_id=${app.id}`"
              >
                <q-tooltip>Consultar historia clínica y recetas emitidas</q-tooltip>
              </q-btn>

              <!-- Menú Adicional para Cancelaciones -->
              <div v-if="['CONFIRMED', 'SCHEDULED'].includes(app.status)" class="w-full text-right sm:text-center md:text-right">
                <q-btn
                  flat
                  dense
                  size="md"
                  color="slate-600"
                  icon="more_horiz"
                  label="Más opciones"
                  no-caps
                  class="text-xs font-medium"
                >
                  <q-menu auto-close>
                    <q-list dense style="min-width: 140px">
                      <q-item clickable class="text-red-600" @click="promptCancelApp(app.id)">
                        <q-item-section avatar>
                          <q-icon name="close" size="16px" />
                        </q-item-section>
                        <q-item-section class="text-xs font-medium">Cancelar Cita</q-item-section>
                      </q-item>
                    </q-list>
                  </q-menu>
                </q-btn>
              </div>

            </div>
          </div>

          <!-- Paginación de Registros Adaptada para Móvil -->
          <div v-if="totalPages > 1" class="flex flex-col sm:flex-row items-center justify-between bg-white px-4 py-3 rounded-2xl border border-slate-200/80 text-xs gap-2">
            <span class="text-slate-500 text-center sm:text-left">
              Página {{ currentPage }} de {{ totalPages }} ({{ filteredAppointments.length }} citas)
            </span>
            <div class="flex items-center gap-1.5">
              <q-btn
                flat
                dense
                round
                icon="chevron_left"
                :disable="currentPage <= 1"
                @click="currentPage--"
                class="min-w-[36px] min-h-[36px]"
              />
              <span class="px-3 py-1 rounded-lg font-black bg-teal-50 text-[#24796a]">{{ currentPage }}</span>
              <q-btn
                flat
                dense
                round
                icon="chevron_right"
                :disable="currentPage >= totalPages"
                @click="currentPage++"
                class="min-w-[36px] min-h-[36px]"
              />
            </div>
          </div>
        </div>

      </div>

    </div>

    <!-- Modal Ficha de Triage y Medidas Antropométricas (Responsive para móvil y tablet) -->
    <q-dialog v-model="showTriageModal">
      <q-card style="width: 95vw; max-width: 580px; max-height: 90vh; border-radius: 20px; display: flex; flex-direction: column;">
        <q-card-section class="bg-[#24796a] text-white flex items-center justify-between p-4 shrink-0">
          <div class="flex items-center space-x-2">
            <q-icon name="monitor_heart" size="22px" />
            <div class="font-bold text-sm sm:text-base">Ficha de Triage y Signos Clínicos</div>
          </div>
          <q-btn flat round dense icon="close" v-close-popup text-color="white" />
        </q-card-section>

        <q-card-section class="p-4 sm:p-5 space-y-4 overflow-y-auto flex-1" v-if="selectedTriageApp">
          <div>
            <span class="text-2xs font-bold text-teal-800 uppercase tracking-wider">Paciente Titular</span>
            <h3 class="text-base sm:text-lg font-black text-slate-900">{{ getPatientDisplayName(selectedTriageApp) }}</h3>
            <p v-if="selectedTriageApp.reason" class="text-xs text-slate-600 mt-0.5">
              Motivo reportado: <em>"{{ selectedTriageApp.reason }}"</em>
            </p>
          </div>

          <div v-if="selectedTriageApp.intake_data" class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 text-center">
              <div class="text-2xs text-slate-500 font-semibold">Estatura</div>
              <div class="text-sm sm:text-base font-black text-slate-800">
                {{ selectedTriageApp.intake_data.height_cm ? `${selectedTriageApp.intake_data.height_cm} cm` : 'N/R' }}
              </div>
            </div>
            <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 text-center">
              <div class="text-2xs text-slate-500 font-semibold">Peso</div>
              <div class="text-sm sm:text-base font-black text-slate-800">
                {{ selectedTriageApp.intake_data.weight_kg ? `${selectedTriageApp.intake_data.weight_kg} kg` : 'N/R' }}
              </div>
            </div>
            <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 text-center">
              <div class="text-2xs text-slate-500 font-semibold">IMC</div>
              <div class="text-sm sm:text-base font-black text-teal-700">
                {{ selectedTriageApp.intake_data.bmi || 'N/R' }}
              </div>
              <div class="text-3xs text-teal-800 font-medium truncate">{{ selectedTriageApp.intake_data.bmi_category || '' }}</div>
            </div>
            <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 text-center">
              <div class="text-2xs text-slate-500 font-semibold">Grupo Sanguíneo</div>
              <div class="text-sm sm:text-base font-black text-red-600">
                {{ selectedTriageApp.intake_data.blood_type || 'N/R' }}
              </div>
            </div>
          </div>

          <div v-if="selectedTriageApp.intake_data" class="space-y-2 text-xs">
            <div class="p-3 bg-red-50/60 rounded-xl border border-red-200/60" v-if="selectedTriageApp.intake_data.allergies">
              <span class="font-bold text-red-800 flex items-center gap-1 mb-0.5">
                <q-icon name="warning" size="14px" class="text-red-700" />
                Alergias Reportadas:
              </span>
              <span class="text-red-950 font-medium">{{ selectedTriageApp.intake_data.allergies }}</span>
            </div>

            <div class="p-3 bg-slate-50 rounded-xl border border-slate-200/80" v-if="selectedTriageApp.intake_data.chronic_conditions">
              <span class="font-bold text-slate-700 flex items-center gap-1 mb-0.5">
                <q-icon name="medical_services" size="14px" class="text-teal-700" />
                Patologías / Antecedentes Crónicos:
              </span>
              <span class="text-slate-800">{{ selectedTriageApp.intake_data.chronic_conditions }}</span>
            </div>

            <div class="p-3 bg-slate-50 rounded-xl border border-slate-200/80" v-if="selectedTriageApp.intake_data.current_medications">
              <span class="font-bold text-slate-700 flex items-center gap-1 mb-0.5">
                <q-icon name="medication" size="14px" class="text-indigo-600" />
                Medicación Habitual:
              </span>
              <span class="text-slate-800">{{ selectedTriageApp.intake_data.current_medications }}</span>
            </div>

            <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-200/60" v-if="selectedTriageApp.intake_data.symptoms">
              <span class="font-bold text-blue-900 flex items-center gap-1 mb-0.5">
                <q-icon name="edit_note" size="16px" class="text-blue-700" />
                Cuadro de Síntomas Detallado:
              </span>
              <span class="text-blue-950">{{ selectedTriageApp.intake_data.symptoms }}</span>
            </div>
          </div>

          <!-- Si el médico está en este modal y la cita está pendiente, permitir aceptarla directo -->
          <div v-if="selectedTriageApp.status === 'PENDING_DOCTOR_APPROVAL'" class="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <q-btn flat label="Cerrar" v-close-popup no-caps />
            <q-btn
              color="teal-8"
              icon="check_circle"
              label="Aceptar Cita"
              no-caps
              class="font-bold rounded-xl bg-[#24796a] text-white"
              @click="doctorAcceptApp(selectedTriageApp.id); showTriageModal = false"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Dialog, Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'

const { user } = useAcl()

const doctorProfile = ref(null)
const appointments = ref([])
const loading = ref(false)
const processingAcceptId = ref(null)

// Selección de fecha y control de visualización
const selectedCalendarDate = ref(null) // Formato 'YYYY/MM/DD'
const activeTab = ref('today') // 'today' | 'future' | 'pending' | 'past' | 'all'
const searchQuery = ref('')
const selectedStatusFilter = ref('')

// Paginación
const currentPage = ref(1)
const itemsPerPage = 15

// Modal de Triage
const showTriageModal = ref(false)
const selectedTriageApp = ref(null)

const tabs = [
  { id: 'today', label: 'Hoy' },
  { id: 'future', label: 'Próximas' },
  { id: 'pending', label: 'Por Aprobar' },
  { id: 'past', label: 'Pasadas' },
  { id: 'all', label: 'Todas' }
]

const statusFilterOptions = [
  { label: 'Todos los estados', value: '' },
  { label: 'Confirmadas', value: 'CONFIRMED' },
  { label: 'Pendientes de Aprobación', value: 'PENDING_DOCTOR_APPROVAL' },
  { label: 'Completadas', value: 'COMPLETED' },
  { label: 'Agendadas', value: 'SCHEDULED' },
  { label: 'Canceladas', value: 'CANCELLED' }
]

// Nombre, Especialidad y Clínica del Médico
const doctorDisplayName = computed(() => {
  if (doctorProfile.value?.full_name) {
    return doctorProfile.value.full_name
  }
  if (appointments.value.length > 0 && appointments.value[0].doctor_name) {
    return appointments.value[0].doctor_name
  }
  return user.value?.name ? `Dr. ${user.value.name}` : 'Dr. Alejandro Morales'
})

const doctorSpecialty = computed(() => {
  return doctorProfile.value?.specialty || 'Ginecología Avanzada • Consulta Activa'
})

const clinicDisplayName = computed(() => {
  if (doctorProfile.value?.clinics && doctorProfile.value.clinics.length > 0) {
    return doctorProfile.value.clinics[0].name
  }
  if (appointments.value.length > 0 && appointments.value[0].clinic_name) {
    return appointments.value[0].clinic_name
  }
  return 'Clínica ÍntimaSalud Central (Sede Principal)'
})

// Fecha formateada en español para el banner
const todayFormattedText = computed(() => {
  const now = new Date()
  return new Intl.DateTimeFormat('es-ES', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(now)
})

// Helper para convertir cualquier fecha a 'YYYY-MM-DD'
function toIsoDateStr (dateVal) {
  if (!dateVal) return ''
  if (typeof dateVal === 'string') {
    return dateVal.slice(0, 10).replace(/\//g, '-')
  }
  const d = new Date(dateVal)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function getTodayIso () {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// Fechas para los eventos del q-date (en formato 'YYYY/MM/DD')
const appointmentDateEvents = computed(() => {
  const setOfDates = new Set()
  for (const a of appointments.value) {
    if (a.start_time) {
      const iso = toIsoDateStr(a.start_time)
      if (iso) {
        setOfDates.add(iso.replace(/-/g, '/'))
      }
    }
  }
  return Array.from(setOfDates)
})

// Conteo de métricas
const countToday = computed(() => {
  const today = getTodayIso()
  return appointments.value.filter(a => toIsoDateStr(a.start_time) === today).length
})

const countFuture = computed(() => {
  const today = getTodayIso()
  return appointments.value.filter(a => toIsoDateStr(a.start_time) > today).length
})

const countPast = computed(() => {
  const today = getTodayIso()
  return appointments.value.filter(a => toIsoDateStr(a.start_time) < today).length
})

const countPending = computed(() => {
  return appointments.value.filter(a => (a.status || '').includes('PENDING')).length
})

function getTabCount (tabId) {
  if (tabId === 'today') return countToday.value
  if (tabId === 'future') return countFuture.value
  if (tabId === 'pending') return countPending.value
  if (tabId === 'past') return countPast.value
  return appointments.value.length
}

const emptyMessage = computed(() => {
  if (selectedCalendarDate.value) {
    return `No tienes citas agendadas para el día ${formatCalendarDateDisplay(selectedCalendarDate.value)}. Puedes seleccionar otra fecha.`
  }
  if (activeTab.value === 'today') {
    return 'No tienes citas programadas para hoy. Puedes revisar tus próximas citas o tu configuración de turnos.'
  }
  if (activeTab.value === 'pending') {
    return 'No hay solicitudes de citas pendientes por aprobar en este momento.'
  }
  if (activeTab.value === 'future') {
    return 'No tienes citas programadas para fechas posteriores.'
  }
  return 'No se encontraron citas que coincidan con los filtros aplicados.'
})

// Filtrado reactivo de citas
const filteredAppointments = computed(() => {
  let list = [...appointments.value]
  const today = getTodayIso()

  // 1. Filtro por Fecha de Calendario (si el usuario hizo clic en una fecha específica)
  if (selectedCalendarDate.value) {
    const targetIso = selectedCalendarDate.value.replace(/\//g, '-')
    list = list.filter(a => toIsoDateStr(a.start_time) === targetIso)
  } else {
    // 2. Filtro por Pestaña
    if (activeTab.value === 'today') {
      list = list.filter(a => toIsoDateStr(a.start_time) === today)
    } else if (activeTab.value === 'future') {
      list = list.filter(a => toIsoDateStr(a.start_time) > today)
    } else if (activeTab.value === 'past') {
      list = list.filter(a => toIsoDateStr(a.start_time) < today)
    } else if (activeTab.value === 'pending') {
      list = list.filter(a => (a.status || '').includes('PENDING'))
    }
  }

  // 3. Filtro por Estado Dropdown
  if (selectedStatusFilter.value) {
    if (selectedStatusFilter.value === 'CANCELLED') {
      list = list.filter(a => (a.status || '').includes('CANCELLED') || (a.status || '').includes('REJECTED'))
    } else {
      list = list.filter(a => a.status === selectedStatusFilter.value)
    }
  }

  // 4. Filtro por Buscador (paciente, teléfono, motivo, sala)
  if (searchQuery.value && searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(a => {
      const name = (a.patient_name || '').toLowerCase()
      const phone = (a.patient_phone || '').toLowerCase()
      const email = (a.patient_email || '').toLowerCase()
      const reason = (a.reason || '').toLowerCase()
      const room = (a.room_name || '').toLowerCase()
      return name.includes(q) || phone.includes(q) || email.includes(q) || reason.includes(q) || room.includes(q)
    })
  }

  // Ordenamiento
  list.sort((a, b) => {
    const timeA = new Date(a.start_time).getTime()
    const timeB = new Date(b.start_time).getTime()
    if (activeTab.value === 'past') {
      return timeB - timeA
    }
    return timeA - timeB
  })

  return list
})

// Paginación
const totalPages = computed(() => {
  return Math.ceil(filteredAppointments.value.length / itemsPerPage) || 1
})

const paginatedAppointments = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  return filteredAppointments.value.slice(start, start + itemsPerPage)
})

// Resetear página al cambiar filtros
watch([selectedCalendarDate, activeTab, searchQuery, selectedStatusFilter], () => {
  currentPage.value = 1
})

// Métodos de selección y navegación
function selectTab (tabId) {
  selectedCalendarDate.value = null
  activeTab.value = tabId
}

function onDateSelect (val) {
  if (val) {
    currentPage.value = 1
  }
}

function clearDateFilter () {
  selectedCalendarDate.value = null
}

function jumpToToday () {
  const todaySlash = getTodayIso().replace(/-/g, '/')
  selectedCalendarDate.value = todaySlash
  activeTab.value = 'today'
}

function resetAllFilters () {
  selectedCalendarDate.value = null
  activeTab.value = 'today'
  searchQuery.value = ''
  selectedStatusFilter.value = ''
  currentPage.value = 1
}

// Cargar Datos
async function fetchDoctorProfile () {
  try {
    const { data } = await api.get('/doctors/me/profile')
    doctorProfile.value = data
  } catch (err) {
    // Silencioso si no está disponible
  }
}

async function fetchAppointments () {
  loading.value = true
  try {
    const { data } = await api.get('/appointments')
    appointments.value = data || []
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: 'Error al consultar las citas del médico.',
      position: 'bottom-right'
    })
  } finally {
    loading.value = false
  }
}

// Acciones del Médico
async function doctorAcceptApp (appId) {
  processingAcceptId.value = appId
  try {
    await api.post(`/appointments/${appId}/doctor-accept`)
    Notify.create({
      type: 'positive',
      message: '¡Cita médica aceptada! Se ha notificado al paciente exitosamente.',
      icon: 'check_circle',
      position: 'top'
    })
    await fetchAppointments()
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al aceptar la cita médica.',
      position: 'top'
    })
  } finally {
    processingAcceptId.value = null
  }
}

function promptDoctorReject (appId) {
  Dialog.create({
    title: 'Rechazar Solicitud de Cita',
    message: 'Indica el motivo justificado por el cual no puedes atender esta solicitud:',
    prompt: {
      model: '',
      type: 'text',
      placeholder: 'Ej. Fuera de disponibilidad o requiere otra especialidad...'
    },
    cancel: true,
    persistent: true,
    ok: { label: 'Rechazar Cita', color: 'negative' }
  }).onOk(async (reason) => {
    try {
      await api.post(`/appointments/${appId}/doctor-reject`, {
        cancellation_reason: reason || 'Rechazada por el médico'
      })
      Notify.create({ type: 'info', message: 'Solicitud rechazada correctamente y horario liberado.' })
      await fetchAppointments()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Error al rechazar cita.' })
    }
  })
}

function promptCancelApp (appId) {
  Dialog.create({
    title: 'Cancelar Cita Médica',
    message: 'Por favor especifica la razón de la cancelación para informar al paciente:',
    prompt: {
      model: '',
      type: 'text',
      placeholder: 'Ej. Imprevisto de fuerza mayor...'
    },
    cancel: true,
    persistent: true,
    ok: { label: 'Confirmar Cancelación', color: 'negative' }
  }).onOk(async (reason) => {
    try {
      await api.post(`/appointments/${appId}/cancel`, {
        cancellation_reason: reason || 'Cancelada por el médico'
      })
      Notify.create({ type: 'warning', message: 'Cita médica cancelada.' })
      await fetchAppointments()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.response?.data?.detail || 'Error al cancelar cita.' })
    }
  })
}

function openTriageModal (app) {
  selectedTriageApp.value = app
  showTriageModal.value = true
}

// Helpers de Formato y Estilos
function formatCalendarDateDisplay (slashDate) {
  if (!slashDate) return ''
  const parts = slashDate.split('/')
  if (parts.length !== 3) return slashDate
  const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10))
  return new Intl.DateTimeFormat('es-ES', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(d)
}

function formatDateDisplay (dateVal) {
  if (!dateVal) return ''
  const d = new Date(dateVal)
  return new Intl.DateTimeFormat('es-ES', {
    weekday: 'short',
    day: 'numeric',
    month: 'short'
  }).format(d)
}

function formatTime (dateVal) {
  if (!dateVal) return ''
  const d = new Date(dateVal)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function calculateDuration (start, end) {
  if (!start || !end) return '30 min'
  const diffMs = new Date(end).getTime() - new Date(start).getTime()
  const diffMin = Math.round(diffMs / (1000 * 60))
  return `${diffMin > 0 ? diffMin : 30} min`
}

function getPatientDisplayName (app) {
  if (app.patient_name && app.patient_name !== 'Paciente Sin Registrar') {
    return app.patient_name
  }
  if (app.patient_email) {
    return app.patient_email.split('@')[0].replace('.', ' ').toUpperCase()
  }
  if (app.patient_phone) {
    return `Paciente (${app.patient_phone})`
  }
  return 'Paciente Consulta'
}

function getPatientInitial (name) {
  if (!name) return 'P'
  return name.trim().charAt(0).toUpperCase()
}

function formatStatus (status) {
  const map = {
    CONFIRMED: 'Confirmada',
    COMPLETED: 'Completada',
    PENDING_DOCTOR_APPROVAL: 'Por Aprobar',
    PENDING_PATIENT_ACCEPTANCE: 'Aceptación Paciente',
    SCHEDULED: 'Agendada',
    CHECKED_IN: 'En Espera',
    IN_CONSULTATION: 'En Consulta',
    CANCELLED_BY_PATIENT: 'Cancelada',
    CANCELLED_BY_DOCTOR: 'Cancelada',
    CANCELLED_BY_CLINIC: 'Cancelada',
    REJECTED_BY_PATIENT: 'Rechazada',
    REJECTED_BY_DOCTOR: 'Rechazada',
    NO_SHOW: 'No Asistió',
    RESCHEDULED: 'Reagendada'
  }
  return map[status] || status || 'Programada'
}

function statusBadgeClass (status) {
  if (status === 'COMPLETED') return 'bg-blue-100 text-blue-800 border border-blue-200'
  if (status === 'CONFIRMED' || status === 'CHECKED_IN' || status === 'IN_CONSULTATION') return 'bg-emerald-100 text-emerald-800 border border-emerald-200'
  if ((status || '').includes('PENDING')) return 'bg-amber-100 text-amber-900 border border-amber-300'
  if ((status || '').includes('CANCELLED') || (status || '').includes('REJECTED') || status === 'NO_SHOW') {
    return 'bg-red-100 text-red-800 border border-red-200'
  }
  return 'bg-slate-100 text-slate-700'
}

function statusDotClass (status) {
  if (status === 'COMPLETED') return 'bg-blue-500'
  if (status === 'CONFIRMED' || status === 'CHECKED_IN' || status === 'IN_CONSULTATION') return 'bg-emerald-500'
  if ((status || '').includes('PENDING')) return 'bg-amber-500 animate-pulse'
  if ((status || '').includes('CANCELLED') || (status || '').includes('REJECTED') || status === 'NO_SHOW') {
    return 'bg-red-500'
  }
  return 'bg-slate-400'
}

function paymentBadgeClass (pStatus) {
  if (pStatus === 'PAID') return 'bg-emerald-50 text-emerald-800 border border-emerald-200'
  return 'bg-amber-50 text-amber-800 border border-amber-200'
}

onMounted(async () => {
  await Promise.all([
    fetchDoctorProfile(),
    fetchAppointments()
  ])
})
</script>
