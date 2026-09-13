<template>
  <q-layout view="lHh Lpr lFf">
    <!-- Header -->
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          aria-label="Menu"
          @click="toggleLeftDrawer"
        />

        <q-toolbar-title class="cursor-pointer flex items-center" @click="$router.push('/')">
          <img src="/icons/vitarecord-logo.png" alt="VitaRecord" class="w-8 h-8 rounded-full bg-white p-0.5 q-mr-sm" />
          <span class="font-bold tracking-tight">VitaRecord</span>
        </q-toolbar-title>

        <div v-if="isLoggedIn" class="row items-center q-gutter-sm">
          <!-- Campana de Notificaciones In-App -->
          <q-btn flat round dense icon="notifications" class="relative-position">

            <q-badge
              v-if="unreadNotificationsCount > 0"
              color="red"
              floating
              rounded
              class="text-2xs font-bold"
            >
              {{ unreadNotificationsCount > 99 ? '99+' : unreadNotificationsCount }}
            </q-badge>
            <q-tooltip>Notificaciones</q-tooltip>

            <q-menu
              anchor="bottom right"
              self="top right"
              :offset="[0, 10]"
              class="rounded-2xl shadow-xl border border-slate-200"
              style="width: 360px; max-width: 90vw;"
              @show="fetchInAppNotifications"
            >
              <div class="p-3 bg-gradient-to-r from-teal-700 to-cyan-700 text-white flex items-center justify-between">
                <div class="flex items-center space-x-2">
                  <q-icon name="notifications" size="18px" />
                  <span class="font-bold text-xs">Centro de Notificaciones</span>
                </div>
                <div class="flex items-center space-x-1">

                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="send"
                    label="Probar"
                    text-color="teal-100"
                    no-caps
                    @click="triggerTestNotification"
                  >
                    <q-tooltip>Emitir aviso de prueba</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="unreadNotificationsCount > 0"
                    flat
                    dense
                    size="xs"
                    label="Marcar leídas"
                    text-color="teal-100"
                    no-caps
                    @click="markAllAsRead"
                  />
                </div>
              </div>


              <!-- Lista de Notificaciones -->
              <q-scroll-area style="height: 320px;">
                <div v-if="loadingNotifications" class="flex justify-center p-6">
                  <q-spinner-dots color="teal" size="30px" />
                </div>

                <div v-else-if="!inAppNotifications.length" class="p-6 text-center text-slate-400">
                  <q-icon name="notifications_none" size="36px" class="opacity-40 mb-2" />
                  <p class="text-xs m-0">No tienes notificaciones recientes.</p>
                </div>

                <q-list v-else separator class="text-slate-800">
                  <q-item
                    v-for="notif in inAppNotifications"
                    :key="notif.id"
                    clickable
                    v-ripple
                    :class="notif.is_read ? 'bg-white opacity-75' : 'bg-teal-50/40 font-medium'"
                    @click="handleNotificationClick(notif)"
                  >
                    <q-item-section avatar top class="min-w-0 pr-2">
                      <div
                        class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs shadow-xs"
                        :class="getNotifIconColor(notif)"
                      >
                        <q-icon :name="getNotifIcon(notif)" size="16px" />
                      </div>
                    </q-item-section>

                    <q-item-section>
                      <q-item-label class="text-xs font-bold leading-snug">
                        {{ notif.metadata_payload?.subject || notif.channel }}
                      </q-item-label>
                      <q-item-label caption class="text-2xs text-slate-600 line-clamp-2 mt-0.5">
                        {{ notif.metadata_payload?.message || notif.error_message || 'Aviso de cita médica o servicio' }}
                      </q-item-label>
                      <q-item-label caption class="text-3xs text-slate-400 mt-1 flex items-center justify-between">
                        <span>{{ formatTimeAgo(notif.sent_at) }}</span>
                        <span v-if="!notif.is_read" class="text-teal-700 font-bold">• Nueva</span>
                      </q-item-label>
                    </q-item-section>
                  </q-item>
                </q-list>
              </q-scroll-area>
            </q-menu>
          </q-btn>

          <q-btn flat round dense icon="logout" @click="logout">
            <q-tooltip>Cerrar Sesión</q-tooltip>
          </q-btn>

        </div>
        <q-btn v-else flat :to="{ name: 'login' }" label="Iniciar sesión" />
      </q-toolbar>
    </q-header>

    <!-- Sidebar / Drawer -->
    <q-drawer
      v-model="leftDrawerOpen"
      show-if-above
      bordered
      class="bg-slate-50 text-slate-800"
      :width="270"
    >
      <div class="p-4 bg-white border-b border-slate-200">
        <div class="flex items-center space-x-3">
          <img
            src="/icons/vitarecord-logo.png"
            alt="VitaRecord"
            class="w-10 h-10 rounded-xl bg-white p-0.5 border border-slate-200 shadow-sm object-contain"
          />
          <div>
            <div class="font-bold text-slate-900 text-sm leading-tight">VitaRecord</div>
            <div class="text-xs text-slate-500">Gestión Clínica y Expediente</div>
          </div>
        </div>

        <div v-if="isLoggedIn" class="mt-4 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
          <div class="text-slate-500 font-medium">Conectado como:</div>
          <div class="font-bold text-slate-900 truncate">{{ userEmail || 'Usuario' }}</div>
          <div class="mt-1">
            <span class="px-2 py-0.5 rounded text-2xs font-semibold bg-blue-100 text-blue-800">
              {{ userRole }}
            </span>
          </div>
        </div>
      </div>

      <q-list padding class="text-slate-700">
        <q-item-label header class="text-xs font-bold text-slate-400 uppercase tracking-wider">
          Principal
        </q-item-label>

        <q-item clickable v-ripple to="/" exact active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600">
          <q-item-section avatar>
            <q-icon name="dashboard" size="20px" />
          </q-item-section>
          <q-item-section>Panel Principal</q-item-section>
        </q-item>

        <q-item
          v-if="userRole !== 'DOCTOR'"
          clickable
          v-ripple
          to="/doctors"
          active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600"
        >
          <q-item-section avatar>
            <q-icon name="medical_services" size="20px" color="teal" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Directorio Médico</q-item-label>
            <q-item-label caption>Especialistas y sedes</q-item-label>
          </q-item-section>
        </q-item>

        <!-- SaaS Master (SuperAdmin) -->
        <template v-if="can('tenants:provision')">
          <q-item-label header class="text-xs font-bold text-indigo-500 uppercase tracking-wider q-mt-md">
            SaaS Master
          </q-item-label>

          <q-item
            clickable
            v-ripple
            to="/admin/clinics"
            active-class="bg-indigo-50 text-indigo-700 font-semibold border-r-4 border-indigo-600"
          >
            <q-item-section avatar>
              <q-icon name="apartment" size="20px" color="indigo" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Clínicas / Tenants</q-item-label>
              <q-item-label caption>Aprovisionamiento</q-item-label>
            </q-item-section>
          </q-item>
        </template>

        <!-- Gestión Médica -->
        <template v-if="can('doctors:verify') || can('doctors:invite')">
          <q-item-label header class="text-xs font-bold text-slate-400 uppercase tracking-wider q-mt-md">
            Gestión Médica
          </q-item-label>

          <q-item
            v-if="can('doctors:verify')"
            clickable
            v-ripple
            to="/admin/doctor-verification"
            active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600"
          >
            <q-item-section avatar>
              <q-icon name="verified_user" size="20px" />
            </q-item-section>
            <q-item-section>Verificación Médica</q-item-section>
          </q-item>

          <q-item v-if="can('doctors:invite')" clickable v-ripple @click="showInviteModal = true">
            <q-item-section avatar>
              <q-icon name="person_add" size="20px" />
            </q-item-section>
            <q-item-section>Invitar Médico</q-item-section>
          </q-item>
        </template>

        <!-- Sede y Consultorios Físicos -->
        <template v-if="can('rooms:read')">
          <q-item-label header class="text-xs font-bold text-teal-600 uppercase tracking-wider q-mt-md">
            Sede y Espacios
          </q-item-label>

          <q-item
            clickable
            v-ripple
            to="/clinic/rooms"
            active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600"
          >
            <q-item-section avatar>
              <q-icon name="meeting_room" size="20px" color="teal" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Consultorios Físicos</q-item-label>
              <q-item-label caption>Mutex lock agenda</q-item-label>
            </q-item-section>
          </q-item>

          <q-item
            v-if="can('staff:manage')"
            clickable
            v-ripple
            to="/clinic/users"
            active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600"
          >
            <q-item-section avatar>
              <q-icon name="manage_accounts" size="20px" color="teal" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Personal y Usuarios</q-item-label>
              <q-item-label caption>Admins, recepción, médicos, pacientes</q-item-label>
            </q-item-section>
          </q-item>
        </template>

        <!-- Agenda Médica -->
        <template v-if="can('doctors:schedule_manage')">
          <q-item-label header class="text-xs font-bold text-teal-600 uppercase tracking-wider q-mt-md">
            Agenda Médica
          </q-item-label>

          <q-item
            clickable
            v-ripple
            to="/doctor/schedule"
            active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600"
          >
            <q-item-section avatar>
              <q-icon name="calendar_month" size="20px" color="teal" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Mi Horario de Atención</q-item-label>
              <q-item-label caption>Disponibilidad Redis</q-item-label>
            </q-item-section>
          </q-item>

          <q-item
            clickable
            v-ripple
            to="/doctor/profile"
            active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600"
          >
            <q-item-section avatar>
              <q-icon name="badge" size="20px" color="teal" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Mi Perfil Profesional</q-item-label>
              <q-item-label caption>Títulos y experiencia pública</q-item-label>
            </q-item-section>
          </q-item>
        </template>

        <!-- Citas y Turnos -->
        <template v-if="can('appointments:book') || can('appointments:manage')">
          <q-item-label header class="text-xs font-bold text-emerald-600 uppercase tracking-wider q-mt-md">
            Citas y Turnos
          </q-item-label>

          <q-item
            v-if="can('appointments:book')"
            clickable
            v-ripple
            to="/appointments/book"
            active-class="bg-emerald-50 text-emerald-700 font-semibold border-r-4 border-emerald-600"
          >
            <q-item-section avatar>
              <q-icon name="event_available" size="20px" color="emerald" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Agendar Cita</q-item-label>
              <q-item-label caption>Familiar o Titular</q-item-label>
            </q-item-section>
          </q-item>

          <q-item
            v-if="can('appointments:manage')"
            clickable
            v-ripple
            to="/appointments/my-list"
            active-class="bg-emerald-50 text-emerald-700 font-semibold border-r-4 border-emerald-600"
          >
            <q-item-section avatar>
              <q-icon name="calendar_today" size="20px" color="emerald" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ userRole === 'PATIENT' ? 'Mis Citas' : 'Gestión de Citas' }}</q-item-label>
              <q-item-label caption>{{ userRole === 'PATIENT' ? 'Historial y estado' : 'Aceptación y estados' }}</q-item-label>
            </q-item-section>
          </q-item>
        </template>

        <!-- Historial y Expediente Clínico (Pacientes) -->
        <template v-if="userRole === 'PATIENT'">
          <q-item-label header class="text-xs font-bold text-teal-600 uppercase tracking-wider q-mt-md">
            Salud y Expediente
          </q-item-label>

          <q-item
            clickable
            v-ripple
            to="/medical/history"
            active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600"
          >
            <q-item-section avatar>
              <q-icon name="folder_shared" size="20px" color="teal" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Mi Historial Clínico</q-item-label>
              <q-item-label caption>Consultas y recetas con QR</q-item-label>
            </q-item-section>
          </q-item>
        </template>

        <!-- Caja y Finanzas -->
        <template v-if="can('payments:view_cashier')">
          <q-item-label header class="text-xs font-bold text-teal-700 uppercase tracking-wider q-mt-md">
            Caja y Ventanilla
          </q-item-label>

          <q-item
            clickable
            v-ripple
            to="/clinic/cashier"
            active-class="bg-teal-50 text-teal-700 font-semibold border-r-4 border-teal-600"
          >
            <q-item-section avatar>
              <q-icon name="point_of_sale" size="20px" color="teal" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Control de Caja</q-item-label>
              <q-item-label caption>Cobros y cuadre diario</q-item-label>
            </q-item-section>
          </q-item>
        </template>

        <!-- Urgencias Médicas & Torre de Control -->
        <template v-if="can('emergency:monitor') || can('emergency:trigger')">
          <q-item-label header class="text-xs font-bold text-red-600 uppercase tracking-wider q-mt-md">
            Urgencias & Radar
          </q-item-label>

          <q-item
            v-if="can('emergency:monitor')"
            clickable
            v-ripple
            to="/admin/control-tower"
            active-class="bg-red-50 text-red-700 font-semibold border-r-4 border-red-600"
          >
            <q-item-section avatar>
              <q-icon name="radar" size="20px" color="negative" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Torre de Control (360°)</q-item-label>
              <q-item-label caption>Monitoreo en vivo</q-item-label>
            </q-item-section>
          </q-item>

          <q-item
            clickable
            v-ripple
            @click="showEmergencyModal = true"
            class="text-negative font-semibold"
          >
            <q-item-section avatar>
              <q-icon name="emergency" size="20px" color="negative" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Activar Alerta SOS</q-item-label>
              <q-item-label caption>Tele-orientación 911</q-item-label>
            </q-item-section>
          </q-item>
        </template>

        <template v-if="['SUPERADMIN', 'MODERATOR'].includes(user?.role)">
          <q-item-label header class="text-xs font-bold text-slate-400 uppercase tracking-wider q-mt-md">
            Seguridad y Cuenta
          </q-item-label>

          <q-item clickable v-ripple @click="openSessionsModal">
            <q-item-section avatar>
              <q-icon name="devices" size="20px" />
            </q-item-section>
            <q-item-section>Sesiones Activas</q-item-section>
          </q-item>

          <q-item clickable v-ripple to="/forgot-password">
            <q-item-section avatar>
              <q-icon name="lock_reset" size="20px" />
            </q-item-section>
            <q-item-section>Restablecer Contraseña</q-item-section>
          </q-item>
        </template>
      </q-list>

      <div class="absolute-bottom p-4 border-t border-slate-200 bg-white">
        <q-btn
          v-if="isLoggedIn"
          outline
          color="negative"
          icon="logout"
          label="Cerrar Sesión"
          class="w-full font-medium"
          no-caps
          @click="logout"
        />
        <q-btn
          v-else
          color="primary"
          icon="login"
          label="Iniciar Sesión"
          to="/login"
          class="w-full font-medium"
          no-caps
        />
      </div>
    </q-drawer>

    <!-- Page Content -->
    <q-page-container class="bg-slate-50">
      <router-view />
    </q-page-container>

    <!-- Modal de Invitar Médico -->
    <q-dialog v-model="showInviteModal">
      <q-card style="min-width: 440px; max-width: 520px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-teal-700 to-cyan-800 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="person_add" size="24px" />
            <h3 class="text-lg font-bold">Invitar Médico a la Clínica</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6 space-y-4">
          <div v-if="inviteResult" class="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2">
            <div class="flex items-center text-emerald-800 font-bold text-sm">
              <q-icon name="check_circle" size="18px" class="mr-2" />
              <span>Invitación generada exitosamente</span>
            </div>
            <p class="text-xs text-slate-600">
              Se ha enviado un correo con el enlace firmado. También puedes copiar el enlace directo a continuación:
            </p>
            <div class="p-2 bg-white rounded border border-emerald-100 text-2xs font-mono break-all text-slate-800 select-all">
              {{ inviteResult.invitation_link }}
            </div>
            <div class="pt-2 flex justify-end">
              <q-btn
                flat
                size="sm"
                color="primary"
                label="Abrir enlace"
                tag="a"
                :href="inviteResult.invitation_link"
                target="_blank"
              />
            </div>
          </div>

          <form v-else class="space-y-4" @submit.prevent="submitInvite">
            <p class="text-xs text-slate-600">
              Ingresa el correo del profesional. Si ya está registrado (Caso A), recibirá enlace de vinculación inmediata. Si es nuevo (Caso B), recibirá enlace de onboarding.
            </p>

            <q-input
              v-model="inviteEmail"
              type="email"
              label="Correo electrónico del médico"
              filled
              required
            />
            <q-input
              v-model="inviteFullName"
              label="Nombre completo (opcional)"
              filled
            />
            <q-input
              v-model="inviteSpecialty"
              label="Especialidad médica (ej. Ginecología)"
              filled
            />
            <q-input
              v-model="invitePhone"
              label="Teléfono / WhatsApp (opcional)"
              filled
            />

            <div v-if="inviteError" class="p-3 bg-red-50 text-red-700 text-xs rounded-lg flex items-center">
              <q-icon name="warning" class="mr-2" size="16px" />
              <span>{{ inviteError }}</span>
            </div>

            <div class="pt-2 flex justify-end space-x-3">
              <q-btn flat label="Cancelar" v-close-popup no-caps />
              <q-btn
                type="submit"
                color="primary"
                label="Generar y Enviar Invitación"
                no-caps
                class="font-semibold"
                :loading="submittingInvite"
              />
            </div>
          </form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Modal de Sesiones Activas -->
    <q-dialog v-model="showSessionsModal">
      <q-card style="min-width: 500px; max-width: 600px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-slate-900 to-slate-800 text-white p-5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="devices" size="24px" />
            <h3 class="text-lg font-bold">Sesiones y Dispositivos Activos</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-6">
          <div v-if="loadingSessions" class="text-center py-8">
            <q-spinner-dots color="primary" size="36px" />
            <p class="text-xs text-slate-500 mt-2">Consultando sesiones...</p>
          </div>

          <div v-else-if="sessionsList.length === 0" class="text-center py-6 text-slate-500 text-sm">
            No se encontraron sesiones registradas.
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="s in sessionsList"
              :key="s.id"
              class="p-3 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between text-xs"
            >
              <div>
                <div class="font-bold text-slate-800 flex items-center">
                  <q-icon name="laptop" class="mr-1 text-primary" size="16px" />
                  <span>{{ s.device_info || 'Dispositivo desconocido' }}</span>
                </div>
                <div class="text-slate-500 mt-0.5">
                  <span>IP: {{ s.ip_address || '127.0.0.1' }}</span>
                  <span class="mx-1">•</span>
                  <span>Emitido: {{ formatDate(s.issued_at) }}</span>
                </div>
              </div>

              <q-btn
                flat
                dense
                round
                color="negative"
                icon="delete"
                @click="revokeSession(s.id)"
              >
                <q-tooltip>Revocar esta sesión</q-tooltip>
              </q-btn>
            </div>
          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="between" class="p-4 bg-slate-50">
          <q-btn
            outline
            color="negative"
            label="Cerrar Todas las Demás Sesiones"
            icon="phonelink_erase"
            no-caps
            class="text-xs"
            @click="revokeAllSessions"
          />
          <q-btn flat label="Cerrar" v-close-popup no-caps />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Modal Global de Urgencia Médica SOS -->
    <EmergencySosModal v-model="showEmergencyModal" />
  </q-layout>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'
import EmergencySosModal from 'src/components/EmergencySosModal.vue'


const router = useRouter()
const leftDrawerOpen = ref(false)
const showEmergencyModal = ref(false)

function toggleLeftDrawer () {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

const { can, hasRole, user, userRole, isLoggedIn, clearAuthToken } = useAcl()

const userEmail = computed(() => {
  return user.value?.email || `${(userRole.value || 'usuario').toLowerCase()}@intimasalud.com`
})

function logout () {
  clearAuthToken()
  router.push({ name: 'login' })
}

// Modal Invitar Médico
const showInviteModal = ref(false)
const inviteEmail = ref('')
const inviteFullName = ref('')
const inviteSpecialty = ref('')
const invitePhone = ref('')
const submittingInvite = ref(false)
const inviteError = ref('')
const inviteResult = ref(null)

async function submitInvite () {
  submittingInvite.value = true
  inviteError.value = ''
  inviteResult.value = null

  try {
    const clinicId = 'c1111111-1111-1111-1111-111111111111'
    const token = localStorage.getItem('access_token')
    const { data } = await api.post(
      `/clinics/${clinicId}/invitations`,
      {
        email: inviteEmail.value,
        full_name: inviteFullName.value || undefined,
        specialty: inviteSpecialty.value || undefined,
        phone: invitePhone.value || undefined
      },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    inviteResult.value = data
  } catch (err) {
    inviteError.value = err.response?.data?.detail || 'No se pudo enviar la invitación.'
  } finally {
    submittingInvite.value = false
  }
}

// Modal Sesiones Activas
const showSessionsModal = ref(false)
const sessionsList = ref([])
const loadingSessions = ref(false)

async function openSessionsModal () {
  showSessionsModal.value = true
  loadingSessions.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.get('/auth/sessions', {
      headers: { Authorization: `Bearer ${token}` }
    })
    sessionsList.value = data
  } catch (err) {
    console.error('Error al obtener sesiones:', err)
  } finally {
    loadingSessions.value = false
  }
}

async function revokeSession (sessionId) {
  try {
    const token = localStorage.getItem('access_token')
    await api.delete(`/auth/sessions/${sessionId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    sessionsList.value = sessionsList.value.filter(s => s.id !== sessionId)
  } catch (err) {
    console.error('Error al revocar sesión:', err)
  }
}

async function revokeAllSessions () {
  try {
    const token = localStorage.getItem('access_token')
    await api.delete('/auth/sessions', {
      headers: { Authorization: `Bearer ${token}` }
    })
    showSessionsModal.value = false
    logout()
  } catch (err) {
    console.error('Error al revocar sesiones:', err)
  }
}

function formatDate (isoStr) {
  if (!isoStr) return 'Reciente'
  try {
    return new Date(isoStr).toLocaleString()
  } catch {
    return isoStr
  }
}

// =====================================================================
// NOTIFICACIONES IN-APP Y TIEMPO REAL
// =====================================================================
const unreadNotificationsCount = ref(0)
const inAppNotifications = ref([])
const loadingNotifications = ref(false)
let notifSocket = null

async function fetchInAppNotifications () {
  if (!isLoggedIn.value) return
  loadingNotifications.value = true
  try {
    const { data } = await api.get('/notifications/my-notifications')
    unreadNotificationsCount.value = data.unread_count || 0
    inAppNotifications.value = data.notifications || []
  } catch (err) {
    console.error('Error al cargar notificaciones in-app:', err)
  } finally {
    loadingNotifications.value = false
  }
}

async function markAllAsRead () {
  try {
    await api.post('/notifications/mark-all-read')
    unreadNotificationsCount.value = 0
    inAppNotifications.value.forEach(n => { n.is_read = true })
  } catch (err) {
    console.error('Error marcando todas como leídas:', err)
  }
}

async function triggerTestNotification () {
  try {
    await api.post('/notifications/test-send', null, {
      params: {
        subject: '¡Prueba In-App Exitosa!',
        message: 'Esta es una notificación de prueba en tiempo real desde ÍntimaSalud.'
      }
    })
    Notify.create({
      type: 'positive',
      message: 'Notificación de prueba emitida con éxito.',
      position: 'top'
    })
    fetchInAppNotifications()
  } catch (err) {
    console.error('Error enviando notificación de prueba:', err)
  }
}

async function handleNotificationClick (notif) {

  if (!notif.is_read) {
    try {
      await api.post(`/notifications/${notif.id}/read`)
      notif.is_read = true
      if (unreadNotificationsCount.value > 0) {
        unreadNotificationsCount.value--
      }
    } catch (e) {
      console.error(e)
    }
  }

  if (notif.appointment_id) {
    router.push('/appointments/my-list')
  } else if (notif.incident_id && can('emergency:monitor')) {
    router.push('/admin/control-tower')
  }
}

function getNotifIcon (notif) {
  const type = notif.metadata_payload?.type || ''
  if (type === 'APPOINTMENT_PROPOSAL') return 'event_available'
  if (type === 'APPOINTMENT_REMINDER') return 'alarm'
  if (type === 'EMERGENCY_DISPATCH') return 'emergency'
  return 'notifications'
}

function getNotifIconColor (notif) {
  const type = notif.metadata_payload?.type || ''
  if (type === 'APPOINTMENT_PROPOSAL') return 'bg-teal-600'
  if (type === 'APPOINTMENT_REMINDER') return 'bg-amber-500'
  if (type === 'EMERGENCY_DISPATCH') return 'bg-red-600'
  return 'bg-blue-600'
}

function formatTimeAgo (isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    const diffMin = Math.round((Date.now() - d.getTime()) / 60000)
    if (diffMin < 1) return 'Ahora mismo'
    if (diffMin < 60) return `Hace ${diffMin} min`
    const diffHours = Math.floor(diffMin / 60)
    if (diffHours < 24) return `Hace ${diffHours} h`
    return d.toLocaleDateString()
  } catch {
    return ''
  }
}

function connectNotificationWebSocket () {
  const token = localStorage.getItem('access_token')
  if (!token) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/v1/notifications/ws?token=${token}`

  try {
    notifSocket = new WebSocket(wsUrl)
    notifSocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.event === 'IN_APP_NOTIFICATION' && payload.data) {
          unreadNotificationsCount.value++
          inAppNotifications.value.unshift({
            id: payload.data.id,
            channel: 'IN_APP',
            status: 'DELIVERED',
            is_read: false,
            sent_at: payload.data.created_at,
            metadata_payload: {
              subject: payload.data.subject,
              message: payload.data.message,
              type: payload.data.metadata?.type,
            },
            appointment_id: payload.data.appointment_id,
            incident_id: payload.data.incident_id,
          })

          Notify.create({
            type: 'info',
            icon: 'notifications_active',
            message: payload.data.subject || 'Aviso en ÍntimaSalud',
            caption: payload.data.message,
            position: 'top-right',
            timeout: 7000,
            actions: [
              {
                label: 'Ver Cita',
                color: 'white',
                handler: () => router.push('/appointments/my-list')
              }
            ]
          })
        }
      } catch (err) {
        console.error('Error parseando websocket notification:', err)
      }
    }

    notifSocket.onclose = () => {
      if (isLoggedIn.value) {
        setTimeout(connectNotificationWebSocket, 6000)
      }
    }
  } catch (err) {
    console.warn('No se pudo establecer WebSocket de notificaciones:', err)
  }
}

onMounted(() => {
  if (isLoggedIn.value) {
    fetchInAppNotifications()
    connectNotificationWebSocket()
  }
})

onUnmounted(() => {
  if (notifSocket) {
    notifSocket.close()
    notifSocket = null
  }
})

</script>
