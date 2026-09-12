<template>
  <q-page class="p-6 bg-slate-50 min-h-screen">
    <div class="max-w-6xl mx-auto space-y-6">
      <!-- Banner de Bienvenida -->
      <div class="bg-gradient-to-r from-teal-700 via-teal-800 to-cyan-900 rounded-3xl p-8 text-white shadow-lg relative overflow-hidden">
        <div class="relative z-10 max-w-2xl">
          <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-xs font-semibold mb-4 text-teal-200">
            <img src="/icons/vitarecord-logo.png" class="w-4 h-4 rounded-full bg-white p-0.5 object-contain inline-block" />
            <span>VitaRecord Suite • Entorno Operativo Clínico</span>
          </div>
          <h1 class="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Panel de Control Clínico
          </h1>
          <p class="mt-2 text-base text-teal-100/90 leading-relaxed">
            Plataforma médica multi-tenant con agendamiento concurrente seguro, verificación formal de matrículas profesionales y flujo de invitaciones omnicanal.
          </p>

          <div class="mt-6 flex flex-wrap gap-3">
            <q-btn
              v-if="can('tenants:provision')"
              color="white"
              text-color="indigo-900"
              icon="apartment"
              label="Gestión de Clínicas"
              to="/admin/clinics"
              no-caps
              class="font-bold shadow-md"
            />
            <q-btn
              v-if="can('doctors:verify')"
              color="white"
              text-color="teal-900"
              icon="verified_user"
              label="Verificación de Médicos"
              to="/admin/doctor-verification"
              no-caps
              class="font-bold shadow-md"
            />
            <q-btn
              v-if="can('rooms:read')"
              color="white"
              text-color="teal-900"
              icon="meeting_room"
              label="Consultorios Físicos"
              to="/clinic/rooms"
              no-caps
              class="font-bold shadow-md"
            />
            <q-btn
              v-if="can('appointments:book')"
              color="white"
              text-color="teal-900"
              icon="event_available"
              label="Agendar Cita"
              to="/appointments/book"
              no-caps
              class="font-bold shadow-md"
            />
            <q-btn
              v-if="can('appointments:manage')"
              color="white"
              text-color="teal-900"
              icon="calendar_today"
              label="Mis Citas"
              to="/appointments/my-list"
              no-caps
              class="font-bold shadow-md"
            />
            <q-btn
              v-if="can('payments:view_cashier')"
              color="white"
              text-color="teal-900"
              icon="point_of_sale"
              label="Control de Caja"
              to="/clinic/cashier"
              no-caps
              class="font-bold shadow-md"
            />
            <q-btn
              v-if="can('emergency:monitor')"
              color="negative"
              icon="radar"
              label="Torre de Control"
              to="/admin/control-tower"
              no-caps
              class="font-bold shadow-md"
            />
            <q-btn
              v-if="can('emergency:trigger')"
              color="negative"
              icon="emergency"
              label="SOS Urgencia"
              @click="showSosModal = true"
              no-caps
              class="font-bold shadow-md"
            />
            <q-btn
              outline
              color="white"
              icon="mail"
              label="Mailpit (:8025)"
              tag="a"
              href="http://localhost:8025"
              target="_blank"
              no-caps
              class="font-medium"
            />
          </div>
        </div>

        <div class="absolute right-0 bottom-0 translate-x-10 translate-y-10 opacity-10 pointer-events-none hidden md:block">
          <q-icon name="medical_services" size="320px" class="text-white" />
        </div>
      </div>

      <!-- Tarjetas de Acciones Rápidas Según Rol y Permisos -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
        <!-- Tarjeta SaaS Master: Clínicas -->
        <div
          v-if="can('tenants:provision')"
          class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
              <q-icon name="apartment" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Aprovisionamiento SaaS</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Gobierno centralizado de tenants clínicos, subdominios seguros, auditoría cruzada y límites de suscripción.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              to="/admin/clinics"
              color="indigo"
              label="Administrar Clínicas"
              icon-right="arrow_forward"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Verificación Médica -->
        <div
          v-if="can('doctors:verify')"
          class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
              <q-icon name="verified" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Verificación Médica</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Módulo 1.5: Dictaminar expedientes médicos, validar números de colegiatura y auditar habilitaciones de especialistas.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              to="/admin/doctor-verification"
              color="primary"
              label="Abrir Cola de Revisión"
              icon-right="arrow_forward"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Consultorios Físicos -->
        <div
          v-if="can('rooms:read')"
          class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
              <q-icon name="meeting_room" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Consultorios y Mutex</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Módulo 2: Configuración de salas físicas con cerrojos de concurrencia pesimistas para impedir dobles turnos en la misma sala.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              to="/clinic/rooms"
              color="teal-800"
              label="Gestionar Consultorios"
              icon-right="arrow_forward"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Agenda Médica -->
        <div
          v-if="can('doctors:schedule_manage')"
          class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="w-12 h-12 rounded-xl bg-cyan-50 text-cyan-700 flex items-center justify-center mb-4">
              <q-icon name="calendar_month" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Mi Agenda y Turnos</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Módulo 2: Definición de franjas horarias semanales, cálculo en tiempo real y aceleración con caché en Redis.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              to="/doctor/schedule"
              color="cyan-800"
              label="Configurar Horario"
              icon-right="arrow_forward"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Agendar Cita -->
        <div
          v-if="can('appointments:book')"
          class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
              <q-icon name="event_available" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Agendar Cita Médica</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Módulo 3: Reserva para titular o familiar con cálculo de turnos libres en Redis y bloqueo pesimista contra dobles reservas.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              to="/appointments/book"
              color="emerald-800"
              label="Reservar Turno"
              icon-right="arrow_forward"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Mis Citas Médicas -->
        <div
          v-if="can('appointments:manage')"
          class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="w-12 h-12 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center mb-4">
              <q-icon name="calendar_today" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Mis Citas Médicas</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Módulo 3: Panel de control del paciente para aceptar citas de recepción, consultar estado de pago o cancelar turnos.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              to="/appointments/my-list"
              color="teal-800"
              label="Ver Mis Citas"
              icon-right="arrow_forward"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Control de Caja -->
        <div
          v-if="can('payments:view_cashier')"
          class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="w-12 h-12 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center mb-4">
              <q-icon name="point_of_sale" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Control de Caja</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Módulo 3: Registro de cobros en recepción (Efectivo, Tarjeta, Pago Móvil, Zelle) y balance contable del día.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              to="/clinic/cashier"
              color="amber-900"
              label="Abrir Cuadre de Caja"
              icon-right="arrow_forward"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Torre de Control 360° -->
        <div
          v-if="can('emergency:monitor')"
          class="bg-white rounded-2xl p-6 shadow-sm border border-red-200 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center mb-4">
              <q-icon name="radar" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Torre de Control 360°</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Módulo 4: Monitoreo en vivo de urgencias médicas, supervisión de SLA de 2 minutos y cadena de escalamiento multicanal.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              to="/admin/control-tower"
              color="negative"
              label="Abrir Torre de Control"
              icon-right="arrow_forward"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Enlaces Rápidos: Mailpit -->
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between">
          <div>
            <div class="w-12 h-12 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center mb-4">
              <q-icon name="forward_to_inbox" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Notificaciones en Vivo</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Consulta en tiempo real los correos enviados por el sistema (invitaciones a médicos, enlaces de onboarding y confirmaciones).
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              tag="a"
              href="http://localhost:8025"
              target="_blank"
              outline
              color="teal-700"
              label="Abrir Mailpit (:8025)"
              icon-right="open_in_new"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>

        <!-- Tarjeta Seguridad y Swagger -->
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between">
          <div>
            <div class="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-4">
              <q-icon name="security" size="28px" />
            </div>
            <h3 class="text-lg font-bold text-slate-900">Seguridad & Swagger API</h3>
            <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">
              Matriz ACL con 15 permisos atómicos, tokens JWT con rotación y detección de reuso, y esquemas OpenAPI interactivos.
            </p>
          </div>
          <div class="mt-6">
            <q-btn
              tag="a"
              href="http://localhost:8000/docs"
              target="_blank"
              outline
              color="purple-800"
              label="Explorar Swagger (:8000)"
              icon-right="api"
              class="w-full font-semibold"
              no-caps
            />
          </div>
        </div>
      </div>

      <!-- Estado de la Arquitectura -->
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/80">
        <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center">
          <q-icon name="dns" size="18px" class="mr-2 text-teal-600" />
          Servicios Locales Conectados
        </h3>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <div class="text-xs text-slate-500 font-medium">Backend API</div>
            <div class="text-sm font-bold text-emerald-600 mt-1 flex items-center justify-center">
              <span class="w-2 h-2 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span>
              FastAPI (:8000)
            </div>
          </div>
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <div class="text-xs text-slate-500 font-medium">Base de Datos</div>
            <div class="text-sm font-bold text-emerald-600 mt-1 flex items-center justify-center">
              <span class="w-2 h-2 rounded-full bg-emerald-500 mr-1.5"></span>
              MySQL 8.0 (:3306)
            </div>
          </div>
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <div class="text-xs text-slate-500 font-medium">Memoria / Cache</div>
            <div class="text-sm font-bold text-emerald-600 mt-1 flex items-center justify-center">
              <span class="w-2 h-2 rounded-full bg-emerald-500 mr-1.5"></span>
              Redis 7 (:6379)
            </div>
          </div>
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <div class="text-xs text-slate-500 font-medium">Servidor Correo</div>
            <div class="text-sm font-bold text-emerald-600 mt-1 flex items-center justify-center">
              <span class="w-2 h-2 rounded-full bg-emerald-500 mr-1.5"></span>
              Mailpit (:8025)
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal SOS para pacientes / trigger directo -->
    <EmergencySosModal v-model="showSosModal" />
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useAcl } from 'src/composables/useAcl'
import EmergencySosModal from 'src/components/EmergencySosModal.vue'

const { can, user, userRole, isLoggedIn } = useAcl()
const showSosModal = ref(false)
</script>
