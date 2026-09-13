<template>
  <q-page class="p-6 max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div>
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold shadow-md shadow-teal-500/20">
            <q-icon name="badge" size="22px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">Personal y Usuarios de la Sede</h1>
            <p class="text-xs text-slate-500">
              Administración de usuarios de tenant (admins, secretarias) y vinculación de usuarios globales (médicos, pacientes).
            </p>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <!-- Selector de Sede para SuperAdmin -->
        <q-select
          v-if="user?.role === 'SUPERADMIN' && clinicOptions.length > 0"
          v-model="activeClinicId"
          :options="clinicOptions"
          option-value="id"
          option-label="name"
          emit-value
          map-options
          dense
          outlined
          rounded
          class="min-w-[240px] text-xs bg-slate-50"
          label="Sede / Clínica"
          @update:model-value="fetchUsers"
        />

        <q-btn
          outline
          color="primary"
          icon="refresh"
          label="Actualizar"
          no-caps
          :loading="loading"
          @click="fetchUsers"
        />

        <q-btn
          v-if="can('staff:manage')"
          color="primary"
          icon="person_add"
          label="Nuevo Usuario / Vincular"
          no-caps
          class="font-semibold shadow-md shadow-teal-600/20"
          @click="openCreateDialog"
        />
      </div>
    </div>

    <!-- Alert / Information Banner -->
    <div class="p-4 bg-teal-50 border border-teal-200 rounded-xl flex items-start gap-3">
      <q-icon name="info" color="teal" size="22px" class="mt-0.5" />
      <div class="text-xs text-teal-950 leading-relaxed space-y-1">
        <div>
          <span class="font-bold">Reglas de Dominio y Acceso:</span>
        </div>
        <ul class="list-disc pl-4 space-y-0.5">
          <li><strong>Administradores y Secretarias:</strong> Son usuarios de sede exclusiva. Solo acceden a este tenant y el administrador puede inactivarlos, reactivarlos, eliminarlos o modificar su rol.</li>
          <li><strong>Médicos y Pacientes:</strong> Son entidades globales de VitaRecord que pueden trabajar o agendar en múltiples sedes. El administrador de la sede <span class="underline font-semibold">no puede inactivar ni eliminar su cuenta general</span>; únicamente puede <strong class="text-orange-900">desvincularlos de esta clínica</strong>.</li>
        </ul>
      </div>
    </div>

    <!-- Filtros de Rol y Buscador -->
    <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex flex-wrap items-center gap-2">
        <q-btn
          v-for="tab in roleTabs"
          :key="tab.value"
          dense
          no-caps
          rounded
          unelevated
          class="px-3 py-1 text-xs transition-all"
          :class="selectedRole === tab.value ? 'bg-teal-700 text-white font-bold shadow-sm' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'"
          @click="selectedRole = tab.value"
        >
          {{ tab.label }}
          <q-badge rounded color="slate" class="ml-1.5 text-2xs" :label="getRoleCount(tab.value)" />
        </q-btn>
      </div>

      <div class="w-full sm:w-72">
        <q-input
          v-model="searchQuery"
          dense
          outlined
          rounded
          placeholder="Buscar por nombre o correo..."
          clearable
          bg-color="white"
          class="text-xs"
        >
          <template #prepend>
            <q-icon name="search" size="18px" color="slate-400" />
          </template>
        </q-input>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center p-12">
      <q-spinner-dots color="primary" size="48px" />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredUsers.length === 0"
      class="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4 shadow-sm"
    >
      <div class="w-16 h-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
        <q-icon name="group_off" size="32px" />
      </div>
      <div>
        <h3 class="text-base font-bold text-slate-800">No se encontraron usuarios</h3>
        <p class="text-xs text-slate-500 max-w-md mx-auto mt-1">
          No hay usuarios registrados ni vinculados activamente que coincidan con los filtros en esta sede.
        </p>
      </div>
      <q-btn
        v-if="can('staff:manage')"
        outline
        color="primary"
        icon="person_add"
        label="Registrar / Vincular"
        no-caps
        class="text-xs font-semibold"
        @click="openCreateDialog"
      />
    </div>

    <!-- Users Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="u in filteredUsers"
        :key="u.id"
        class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4 relative overflow-hidden"
      >
        <!-- Top row: Avatar + Role badge + Entity scope badge -->
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center space-x-3 min-w-0">
            <div
              class="w-11 h-11 rounded-xl flex items-center justify-center font-bold text-sm text-white shrink-0"
              :class="getAvatarClass(u.role)"
            >
              {{ getInitials(u.full_name || u.email) }}
            </div>
            <div class="min-w-0">
              <h3 class="font-bold text-slate-900 text-sm truncate" :title="u.full_name || 'Sin nombre'">
                {{ u.full_name || 'Usuario sin nombre' }}
              </h3>
              <p class="text-xs text-slate-500 truncate" :title="u.email">
                {{ u.email }}
              </p>
            </div>
          </div>
        </div>

        <!-- Middle: Role, Scope & Status details -->
        <div class="space-y-2 border-y border-slate-100 py-3 text-xs">
          <div class="flex items-center justify-between">
            <span class="text-slate-500">Rol:</span>
            <span
              class="px-2 py-0.5 rounded-full font-semibold text-2xs"
              :class="getRoleBadgeClass(u.role)"
            >
              {{ getRoleLabel(u.role) }}
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-slate-500">Tipo de Entidad:</span>
            <span
              class="px-2 py-0.5 rounded-full text-2xs font-medium"
              :class="isTenantUser(u) ? 'bg-blue-50 text-blue-800 border border-blue-200' : 'bg-purple-50 text-purple-800 border border-purple-200'"
            >
              {{ isTenantUser(u) ? 'Usuario de Sede' : 'Usuario Global' }}
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-slate-500">Estado de Cuenta:</span>
            <span
              class="px-2 py-0.5 rounded-full font-semibold text-2xs flex items-center gap-1"
              :class="getStatusBadgeClass(u.status)"
            >
              <q-icon :name="getStatusIcon(u.status)" size="12px" />
              {{ getStatusLabel(u.status) }}
            </span>
          </div>

          <div v-if="u.phone" class="flex items-center justify-between">
            <span class="text-slate-500">Teléfono:</span>
            <span class="font-mono text-slate-700">{{ u.phone }}</span>
          </div>

          <!-- Doctor details -->
          <div v-if="u.role === 'DOCTOR' && u.specialty" class="flex items-center justify-between">
            <span class="text-slate-500">Especialidad:</span>
            <span class="font-semibold text-teal-800 text-right truncate max-w-[170px]">{{ u.specialty }}</span>
          </div>

          <div v-if="u.role === 'DOCTOR' && u.license_number" class="flex items-center justify-between">
            <span class="text-slate-500">Matrícula:</span>
            <span class="font-mono text-slate-700">{{ u.license_number }}</span>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="flex items-center justify-between pt-1 gap-2 flex-wrap">
          <!-- Reenviar Invitación / Clave -->
          <q-btn
            flat
            dense
            color="primary"
            icon="forward_to_inbox"
            label="Reenviar Clave"
            no-caps
            class="text-xs font-semibold"
            :loading="actionLoadingId === u.id"
            @click="resendInvite(u)"
          >
            <q-tooltip>Reenviar correo para configurar contraseña</q-tooltip>
          </q-btn>

          <!-- Acciones para Usuario de Tenant (Admin / Secretaria) -->
          <template v-if="isTenantUser(u)">
            <div class="flex items-center gap-1">
              <!-- Cambiar Rol -->
              <q-btn
                v-if="u.id !== user?.id"
                flat
                dense
                color="secondary"
                icon="swap_horiz"
                label="Rol"
                no-caps
                class="text-xs"
                @click="openChangeRoleDialog(u)"
              >
                <q-tooltip>Cambiar entre Administrador y Secretaria</q-tooltip>
              </q-btn>

              <!-- Inactivar / Reactivar -->
              <q-btn
                v-if="u.id !== user?.id"
                flat
                dense
                :color="u.status === 'DEACTIVATED' ? 'positive' : 'negative'"
                :icon="u.status === 'DEACTIVATED' ? 'check_circle' : 'block'"
                :label="u.status === 'DEACTIVATED' ? 'Reactivar' : 'Desactivar'"
                no-caps
                class="text-xs"
                :loading="toggleLoadingId === u.id"
                @click="confirmToggleTenantUserStatus(u)"
              >
                <q-tooltip>{{ u.status === 'DEACTIVATED' ? 'Habilitar acceso a la clínica' : 'Desactivar acceso a la clínica' }}</q-tooltip>
              </q-btn>
            </div>
          </template>

          <!-- Acciones para Usuario Global (Médico / Paciente) -->
          <template v-else>
            <!-- Desvincular de la Sede -->
            <q-btn
              flat
              dense
              color="deep-orange-9"
              icon="link_off"
              label="Desvincular"
              no-caps
              class="text-xs font-semibold"
              :loading="toggleLoadingId === u.id"
              @click="confirmDisaffiliate(u)"
            >
              <q-tooltip>Desvincular de esta sede (su cuenta general permanece activa)</q-tooltip>
            </q-btn>
          </template>
        </div>
      </div>
    </div>

    <!-- Create User Dialog with Two Tabs: Vincular existente & Crear y vincular -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 540px; max-width: 720px; width: 100%; border-radius: 16px;" class="overflow-hidden">
        <!-- Card Header with Gradient and Tabs -->
        <q-card-section class="bg-gradient-to-r from-teal-700 to-cyan-800 text-white p-5 pb-0">
          <div class="flex items-center justify-between pb-3">
            <div class="flex items-center space-x-2">
              <q-icon name="person_add" size="24px" />
              <h3 class="text-lg font-bold">Gestión de Personal y Vinculaciones</h3>
            </div>
            <q-btn flat round dense icon="close" text-color="white" v-close-popup />
          </div>

          <q-tabs
            v-model="activeModalTab"
            dense
            class="text-teal-100"
            active-color="white"
            indicator-color="amber-400"
            align="justify"
            narrow-indicator
          >
            <q-tab name="link_existing" icon="person_search" label="Vincular existente" no-caps class="font-semibold text-sm" />
            <q-tab name="create_new" icon="person_add_alt" label="Crear y vincular" no-caps class="font-semibold text-sm" />
          </q-tabs>
        </q-card-section>

        <!-- Tab Panels -->
        <q-tab-panels v-model="activeModalTab" animated class="p-0">
          <!-- TAB 1: Vincular existente -->
          <q-tab-panel name="link_existing" class="p-6 space-y-4">
            <div class="p-3.5 bg-teal-50 border border-teal-200 rounded-xl text-xs text-teal-900 leading-relaxed flex items-start gap-2.5">
              <q-icon name="manage_search" color="teal" size="20px" class="mt-0.5 shrink-0" />
              <div>
                <strong>Buscador global de médicos en VitaRecord:</strong>
                <p class="mt-0.5 text-slate-600">
                  Busca profesionales médicos por <strong>nombre</strong>, <strong>correo electrónico</strong>, <strong>cédula</strong> o <strong>matrícula profesional</strong> para afiliarlo a esta sede de inmediato o enviarle una invitación.
                </p>
              </div>
            </div>

            <!-- Buscador Input -->
            <div class="flex gap-2 items-center">
              <q-input
                v-model="doctorSearchQuery"
                outlined
                dense
                placeholder="Buscar por nombre, correo, cédula o matrícula médica..."
                class="flex-1 text-xs"
                clearable
                @update:model-value="onDoctorSearchInput"
                @keyup.enter="searchDoctorsToAffiliate"
              >
                <template #prepend>
                  <q-icon name="search" color="teal" />
                </template>
              </q-input>
              <q-btn
                color="primary"
                icon="search"
                label="Buscar"
                dense
                no-caps
                class="px-4 h-[40px] font-semibold"
                :loading="searchingDoctors"
                @click="searchDoctorsToAffiliate"
              />
            </div>

            <!-- Loading Spinner -->
            <div v-if="searchingDoctors" class="py-8 text-center text-teal-700 space-y-2">
              <q-spinner-dots size="36px" color="teal" />
              <p class="text-xs text-slate-500">Buscando profesionales en VitaRecord...</p>
            </div>

            <!-- Resultados de Búsqueda -->
            <div v-else-if="doctorSearchResults.length > 0" class="space-y-3 max-h-96 overflow-y-auto pr-1">
              <div
                v-for="doc in doctorSearchResults"
                :key="doc.id"
                class="p-4 rounded-xl border border-slate-200 bg-white hover:border-teal-300 hover:shadow-sm transition-all space-y-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="flex items-center space-x-3 min-w-0">
                    <q-avatar size="44px" color="teal-1" text-color="teal-9" class="font-bold border border-teal-200">
                      <img v-if="doc.profile_picture_url" :src="doc.profile_picture_url" />
                      <span v-else>{{ getInitials(doc.full_name || doc.email) }}</span>
                    </q-avatar>
                    <div class="min-w-0">
                      <div class="flex items-center gap-2">
                        <h4 class="text-sm font-bold text-slate-900 truncate">
                          {{ doc.full_name || 'Médico sin nombre' }}
                        </h4>
                        <q-badge v-if="doc.specialty" color="teal-1" text-color="teal-9" class="text-2xs font-semibold">
                          {{ doc.specialty }}
                        </q-badge>
                      </div>
                      <p class="text-xs text-slate-500 truncate flex items-center gap-1 mt-0.5">
                        <q-icon name="mail" size="14px" color="slate-400" />
                        {{ doc.email }}
                        <span v-if="doc.phone" class="ml-2 flex items-center gap-1">
                          <q-icon name="phone" size="14px" color="slate-400" />
                          {{ doc.phone }}
                        </span>
                      </p>
                    </div>
                  </div>

                  <!-- Badges / Acciones -->
                  <div class="shrink-0 flex flex-col items-end gap-1.5">
                    <div v-if="doc.is_already_affiliated">
                      <q-badge color="positive" class="p-1.5 text-2xs font-bold" icon="check_circle">
                        Ya Afiliado
                      </q-badge>
                    </div>
                    <div v-else-if="doc.affiliation_status === 'PENDING'">
                      <q-badge color="amber-8" class="p-1.5 text-2xs font-bold" icon="hourglass_top">
                        Invitación Pendiente
                      </q-badge>
                    </div>
                    <div v-else class="flex items-center gap-2">
                      <q-btn
                        size="sm"
                        color="teal"
                        icon="link"
                        label="Vincular Directamente"
                        no-caps
                        class="font-semibold shadow-sm"
                        :loading="affiliatingDoctorId === doc.id"
                        @click="affiliateDoctor(doc, 'DIRECT')"
                      >
                        <q-tooltip>Vincular y activar de inmediato a esta clínica</q-tooltip>
                      </q-btn>
                      <q-btn
                        size="sm"
                        outline
                        color="primary"
                        icon="send"
                        label="Enviar Invitación"
                        no-caps
                        class="font-semibold"
                        :loading="affiliatingDoctorId === doc.id"
                        @click="affiliateDoctor(doc, 'INVITE')"
                      >
                        <q-tooltip>Enviar correo formal de invitación</q-tooltip>
                      </q-btn>
                    </div>
                  </div>
                </div>

                <!-- Fila de Identificación y Matrícula -->
                <div class="grid grid-cols-2 gap-2 text-2xs pt-2 border-t border-slate-100 text-slate-600">
                  <div class="flex items-center gap-1.5">
                    <q-icon name="badge" size="14px" color="teal" />
                    <span>Cédula / DNI: <strong>{{ doc.identification_number || 'No registrada' }}</strong></span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <q-icon name="verified_user" size="14px" color="teal" />
                    <span>Matrícula Médica: <strong>{{ doc.license_number || 'No registrada' }}</strong></span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Sin resultados tras buscar -->
            <div v-else-if="doctorSearchPerformed" class="p-6 bg-slate-50 border border-dashed border-slate-300 rounded-xl text-center space-y-3">
              <q-icon name="person_search" size="36px" color="slate-400" />
              <div>
                <p class="text-xs font-semibold text-slate-700">No se encontró ningún profesional con ese término</p>
                <p class="text-2xs text-slate-500 mt-1">Verifica el nombre, correo o cédula, o créalo como nuevo profesional en la otra pestaña.</p>
              </div>
              <q-btn
                outline
                dense
                color="primary"
                icon="person_add_alt"
                label="Crear y vincular como nuevo profesional"
                no-caps
                class="text-xs font-semibold px-3 py-1"
                @click="switchToCreateDoctor"
              />
            </div>

            <!-- Estado inicial antes de buscar -->
            <div v-else class="p-8 text-center text-slate-400 space-y-2">
              <q-icon name="search" size="40px" class="opacity-40" />
              <p class="text-xs">Escribe el nombre, correo, cédula o matrícula del médico para comenzar la búsqueda.</p>
            </div>
          </q-tab-panel>

          <!-- TAB 2: Crear y vincular -->
          <q-tab-panel name="create_new" class="p-6 space-y-4">
            <div class="p-3 bg-teal-50 border border-teal-200 rounded-xl text-xs text-teal-900 leading-relaxed space-y-1">
              <div class="font-bold flex items-center gap-1.5">
                <q-icon name="mail" color="teal" size="16px" />
                Gestión de Cuentas:
              </div>
              <div>
                • <strong>Médicos y Pacientes:</strong> Si el usuario no existe, se creará su cuenta en VitaRecord y recibirá correo para activar su contraseña y perfil.
              </div>
              <div>
                • <strong>Administradores y Secretarias:</strong> Son exclusivos de esta sede y su correo debe ser único en el sistema.
              </div>
            </div>

            <form class="space-y-4" @submit.prevent="submitCreateUser">
              <!-- Rol -->
              <q-select
                v-model="form.role"
                :options="creatableRoleOptions"
                emit-value
                map-options
                label="Rol de Usuario *"
                filled
                required
              >
                <template #prepend>
                  <q-icon name="admin_panel_settings" color="teal" />
                </template>
              </q-select>

              <!-- Nombre Completo -->
              <q-input
                v-model="form.full_name"
                label="Nombre y Apellido *"
                placeholder="Ej. Dra. Carmen Morales"
                filled
                required
              >
                <template #prepend>
                  <q-icon name="person" color="teal" />
                </template>
              </q-input>

              <!-- Correo Electrónico -->
              <q-input
                v-model="form.email"
                label="Correo Electrónico *"
                placeholder="ejemplo@intimasalud.com"
                type="email"
                filled
                required
              >
                <template #prepend>
                  <q-icon name="email" color="teal" />
                </template>
              </q-input>

              <!-- Teléfono -->
              <q-input
                v-model="form.phone"
                label="Teléfono Móvil (Opcional)"
                placeholder="+58 412 1234567"
                filled
              >
                <template #prepend>
                  <q-icon name="phone" color="teal" />
                </template>
              </q-input>

              <!-- Campos específicos para Médicos -->
              <div v-if="form.role === 'DOCTOR'" class="space-y-4 pt-2 border-t border-slate-200">
                <p class="text-xs font-bold text-slate-700 flex items-center gap-1">
                  <q-icon name="medical_services" color="teal" />
                  Información Profesional del Médico
                </p>

                <q-select
                  v-model="form.specialty"
                  :options="specialtyOptions"
                  label="Especialidad Médica"
                  filled
                  clearable
                  use-input
                  new-value-mode="add-unique"
                />

                <q-input
                  v-model="form.license_number"
                  label="Matrícula / Licencia Médica"
                  placeholder="Ej. MPPS-84920"
                  filled
                />
              </div>

              <div v-if="formError" class="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
                <q-icon name="error" color="negative" size="18px" />
                <span>{{ formError }}</span>
              </div>

              <div class="flex justify-end space-x-3 pt-4 border-t border-slate-100">
                <q-btn flat label="Cancelar" no-caps v-close-popup />
                <q-btn
                  type="submit"
                  color="primary"
                  label="Crear y Vincular"
                  icon="person_add"
                  no-caps
                  class="font-semibold"
                  :loading="submitting"
                />
              </div>
            </form>
          </q-tab-panel>
        </q-tab-panels>
      </q-card>
    </q-dialog>

    <!-- Dialog para Cambiar Rol de Usuario de Tenant -->
    <q-dialog v-model="showRoleDialog">
      <q-card style="min-width: 360px; border-radius: 16px;">
        <q-card-section class="bg-teal-700 text-white p-4 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="swap_horiz" size="22px" />
            <h3 class="font-bold text-sm">Modificar Rol de Sede</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-5 space-y-4">
          <p class="text-xs text-slate-600">
            Selecciona el nuevo rol para <strong>{{ roleTargetUser?.full_name || roleTargetUser?.email }}</strong>:
          </p>

          <q-select
            v-model="newRoleSelection"
            :options="tenantRoleOptions"
            emit-value
            map-options
            label="Rol de Sede"
            filled
          />

          <div class="flex justify-end space-x-3 pt-3">
            <q-btn flat label="Cancelar" no-caps v-close-popup />
            <q-btn
              color="primary"
              label="Actualizar Rol"
              no-caps
              class="font-semibold"
              :loading="roleUpdating"
              @click="submitChangeRole"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Dialog, Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'

const { can, user } = useAcl()

const DEFAULT_CLINIC_ID = 'c1111111-1111-1111-1111-111111111111'
const activeClinicId = ref(user.value?.clinicId || DEFAULT_CLINIC_ID)
const clinicOptions = ref([])

const users = ref([])
const loading = ref(false)
const submitting = ref(false)
const showCreateDialog = ref(false)
const activeModalTab = ref('link_existing')
const doctorSearchQuery = ref('')
const doctorSearchResults = ref([])
const searchingDoctors = ref(false)
const doctorSearchPerformed = ref(false)
const affiliatingDoctorId = ref(null)
let searchDebounceTimeout = null
const formError = ref('')
const selectedRole = ref('ALL')
const searchQuery = ref('')
const actionLoadingId = ref(null)
const toggleLoadingId = ref(null)

const showRoleDialog = ref(false)
const roleTargetUser = ref(null)
const newRoleSelection = ref('RECEPTIONIST')
const roleUpdating = ref(false)

const roleTabs = [
  { label: 'Todos', value: 'ALL' },
  { label: 'Administradores', value: 'CLINIC_ADMIN' },
  { label: 'Secretarias', value: 'RECEPTIONIST' },
  { label: 'Médicos', value: 'DOCTOR' },
  { label: 'Pacientes', value: 'PATIENT' }
]

const creatableRoleOptions = [
  { label: 'Administrador de Sede / Clínica (Tenant Admin)', value: 'CLINIC_ADMIN' },
  { label: 'Secretaria / Recepcionista', value: 'RECEPTIONIST' },
  { label: 'Médico Especialista', value: 'DOCTOR' },
  { label: 'Paciente', value: 'PATIENT' }
]

const tenantRoleOptions = [
  { label: 'Administrador de Sede (Tenant Admin)', value: 'CLINIC_ADMIN' },
  { label: 'Secretaria / Recepcionista', value: 'RECEPTIONIST' }
]

const specialtyOptions = [
  'Ginecología & Obstetricia',
  'Medicina Materno-Fetal',
  'Fertilidad & Reproducción Asistida',
  'Ginecología Oncológica',
  'Mastología & Patología Mamaria',
  'Endocrinología Ginecológica',
  'Urología Ginecológica & Piso Pélvico',
  'Perinatología & Alto Riesgo',
  'Pediatría',
  'Medicina Interna',
  'Medicina General'
]

const form = reactive({
  role: 'RECEPTIONIST',
  full_name: '',
  email: '',
  phone: '',
  specialty: null,
  license_number: ''
})

function resetForm () {
  form.role = 'RECEPTIONIST'
  form.full_name = ''
  form.email = ''
  form.phone = ''
  form.specialty = null
  form.license_number = ''
  formError.value = ''
}

function isTenantUser (u) {
  return ['CLINIC_ADMIN', 'RECEPTIONIST'].includes(u.role)
}

const filteredUsers = computed(() => {
  let list = users.value
  if (selectedRole.value !== 'ALL') {
    list = list.filter(u => u.role === selectedRole.value)
  }
  if (searchQuery.value && searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(u =>
      (u.full_name && u.full_name.toLowerCase().includes(q)) ||
      (u.email && u.email.toLowerCase().includes(q))
    )
  }
  return list
})

function getRoleCount (roleVal) {
  if (roleVal === 'ALL') return users.value.length
  return users.value.filter(u => u.role === roleVal).length
}

function getInitials (name) {
  if (!name) return 'U'
  const parts = name.trim().split(' ')
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

function getAvatarClass (role) {
  switch (role) {
    case 'CLINIC_ADMIN': return 'bg-purple-600'
    case 'DOCTOR': return 'bg-teal-600'
    case 'RECEPTIONIST': return 'bg-sky-600'
    case 'PATIENT': return 'bg-emerald-600'
    default: return 'bg-slate-600'
  }
}

function getRoleLabel (role) {
  switch (role) {
    case 'CLINIC_ADMIN': return 'Administrador'
    case 'DOCTOR': return 'Médico'
    case 'RECEPTIONIST': return 'Secretaria / Recepción'
    case 'PATIENT': return 'Paciente'
    default: return role
  }
}

function getRoleBadgeClass (role) {
  switch (role) {
    case 'CLINIC_ADMIN': return 'bg-purple-50 text-purple-800 border border-purple-200'
    case 'DOCTOR': return 'bg-teal-50 text-teal-800 border border-teal-200'
    case 'RECEPTIONIST': return 'bg-sky-50 text-sky-800 border border-sky-200'
    case 'PATIENT': return 'bg-emerald-50 text-emerald-800 border border-emerald-200'
    default: return 'bg-slate-100 text-slate-700'
  }
}

function getStatusLabel (status) {
  switch (status) {
    case 'ACTIVE': return 'Activo'
    case 'PENDING_ONBOARDING': return 'Pendiente de Clave'
    case 'DEACTIVATED': return 'Desactivado'
    case 'SUSPENDED': return 'Suspendido'
    default: return status
  }
}

function getStatusBadgeClass (status) {
  switch (status) {
    case 'ACTIVE': return 'bg-emerald-50 text-emerald-800 border border-emerald-200'
    case 'PENDING_ONBOARDING': return 'bg-amber-50 text-amber-800 border border-amber-200'
    case 'DEACTIVATED': return 'bg-rose-50 text-rose-800 border border-rose-200'
    default: return 'bg-slate-100 text-slate-600'
  }
}

function getStatusIcon (status) {
  switch (status) {
    case 'ACTIVE': return 'check_circle'
    case 'PENDING_ONBOARDING': return 'schedule'
    case 'DEACTIVATED': return 'block'
    default: return 'help'
  }
}

async function fetchClinics () {
  if (user.value?.role !== 'SUPERADMIN') return
  try {
    const res = await api.get('/clinics')
    clinicOptions.value = res.data
    if (!activeClinicId.value && res.data.length > 0) {
      activeClinicId.value = res.data[0].id
    }
  } catch (err) {
    console.error('Error cargando clínicas:', err)
  }
}

async function fetchUsers () {
  const clinicId = activeClinicId.value || user.value?.clinicId || DEFAULT_CLINIC_ID
  loading.value = true
  try {
    const res = await api.get(`/clinics/${clinicId}/users`)
    users.value = res.data
  } catch (err) {
    console.error('Error cargando usuarios:', err)
    Notify.create({
      type: 'negative',
      message: 'No se pudieron cargar los usuarios de la clínica.',
      position: 'bottom-right'
    })
  } finally {
    loading.value = false
  }
}

function openCreateDialog () {
  resetForm()
  activeModalTab.value = 'link_existing'
  doctorSearchQuery.value = ''
  doctorSearchResults.value = []
  doctorSearchPerformed.value = false
  showCreateDialog.value = true
}

function onDoctorSearchInput (val) {
  if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout)
  if (!val || val.trim().length < 2) {
    doctorSearchResults.value = []
    doctorSearchPerformed.value = false
    return
  }
  searchDebounceTimeout = setTimeout(() => {
    searchDoctorsToAffiliate()
  }, 400)
}

async function searchDoctorsToAffiliate () {
  if (!doctorSearchQuery.value || doctorSearchQuery.value.trim().length < 2) {
    doctorSearchResults.value = []
    doctorSearchPerformed.value = false
    return
  }
  searchingDoctors.value = true
  doctorSearchPerformed.value = true
  try {
    const clinicId = activeClinicId.value || user.value?.clinicId || DEFAULT_CLINIC_ID
    const res = await api.get(`/clinics/${clinicId}/doctors/search-to-affiliate`, {
      params: { q: doctorSearchQuery.value.trim() }
    })
    doctorSearchResults.value = res.data || []
  } catch (err) {
    console.error('Error buscando médicos:', err)
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al buscar profesionales médicos.',
      position: 'bottom-right'
    })
  } finally {
    searchingDoctors.value = false
  }
}

async function affiliateDoctor (doctor, mode = 'DIRECT') {
  const clinicId = activeClinicId.value || user.value?.clinicId || DEFAULT_CLINIC_ID
  affiliatingDoctorId.value = doctor.id
  try {
    const res = await api.post(
      `/clinics/${clinicId}/doctors/${doctor.id}/affiliate`,
      { mode },
      { params: { mode } }
    )
    Notify.create({
      type: 'positive',
      message: res.data?.message || (mode === 'DIRECT' ? `Médico ${doctor.full_name || doctor.email} vinculado exitosamente.` : `Invitación enviada a ${doctor.email}.`),
      position: 'bottom-right',
      icon: 'verified'
    })
    if (mode === 'DIRECT') {
      doctor.is_already_affiliated = true
      doctor.affiliation_status = 'ACTIVE'
    } else {
      doctor.affiliation_status = 'PENDING'
    }
    await fetchUsers()
  } catch (err) {
    console.error('Error afiliando médico:', err)
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al vincular el profesional a la clínica.',
      position: 'bottom-right'
    })
  } finally {
    affiliatingDoctorId.value = null
  }
}

function switchToCreateDoctor () {
  form.role = 'DOCTOR'
  const q = (doctorSearchQuery.value || '').trim()
  if (q.includes('@')) {
    form.email = q
  } else if (/^\d+$/.test(q)) {
    form.license_number = q
  } else if (q.length > 0) {
    form.full_name = q
  }
  activeModalTab.value = 'create_new'
}

async function submitCreateUser () {
  formError.value = ''
  submitting.value = true
  const clinicId = activeClinicId.value || user.value?.clinicId || DEFAULT_CLINIC_ID

  try {
    const payload = {
      role: form.role,
      full_name: form.full_name,
      email: form.email,
      phone: form.phone || null,
      specialty: form.role === 'DOCTOR' ? form.specialty : null,
      license_number: form.role === 'DOCTOR' ? form.license_number : null
    }

    const res = await api.post(`/clinics/${clinicId}/users`, payload)
    Notify.create({
      type: 'positive',
      message: `Operación exitosa: ${res.data.full_name} (${getRoleLabel(res.data.role)}).`,
      position: 'bottom-right',
      icon: 'mark_email_read'
    })

    showCreateDialog.value = false
    await fetchUsers()
  } catch (err) {
    console.error('Error creando usuario:', err)
    const detail = err.response?.data?.detail
    if (err.response?.status === 409) {
      formError.value = detail || 'El correo electrónico ya se encuentra registrado con otro rol o vinculado a esta sede.'
    } else {
      formError.value = detail || 'Ocurrió un error al procesar el usuario.'
    }
  } finally {
    submitting.value = false
  }
}

async function resendInvite (targetUser) {
  const clinicId = activeClinicId.value || user.value?.clinicId || DEFAULT_CLINIC_ID
  actionLoadingId.value = targetUser.id

  try {
    await api.post(`/clinics/${clinicId}/users/${targetUser.id}/resend-invite`)
    Notify.create({
      type: 'positive',
      message: `Enlace para configurar contraseña reenviado a ${targetUser.email}`,
      position: 'bottom-right',
      icon: 'send'
    })
  } catch (err) {
    console.error('Error reenviando invitación:', err)
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al reenviar la invitación.',
      position: 'bottom-right'
    })
  } finally {
    actionLoadingId.value = null
  }
}

function openChangeRoleDialog (targetUser) {
  roleTargetUser.value = targetUser
  newRoleSelection.value = targetUser.role === 'CLINIC_ADMIN' ? 'RECEPTIONIST' : 'CLINIC_ADMIN'
  showRoleDialog.value = true
}

async function submitChangeRole () {
  if (!roleTargetUser.value) return
  roleUpdating.value = true
  const clinicId = activeClinicId.value || user.value?.clinicId || DEFAULT_CLINIC_ID

  try {
    const res = await api.patch(`/clinics/${clinicId}/users/${roleTargetUser.value.id}/role`, {
      role: newRoleSelection.value
    })
    roleTargetUser.value.role = res.data.role
    Notify.create({
      type: 'positive',
      message: `Rol actualizado a ${getRoleLabel(res.data.role)}.`,
      position: 'bottom-right'
    })
    showRoleDialog.value = false
  } catch (err) {
    console.error('Error modificando rol:', err)
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudo actualizar el rol.',
      position: 'bottom-right'
    })
  } finally {
    roleUpdating.value = false
  }
}

function confirmToggleTenantUserStatus (targetUser) {
  const isDeactivating = targetUser.status !== 'DEACTIVATED'
  const actionText = isDeactivating ? 'desactivar' : 'reactivar'

  Dialog.create({
    title: `¿Confirmar ${actionText}?`,
    message: `¿Estás seguro de que deseas ${actionText} a ${targetUser.full_name || targetUser.email}? Este usuario pertenece exclusivamente a esta clínica.`,
    cancel: true,
    persistent: true,
    ok: {
      label: isDeactivating ? 'Desactivar' : 'Reactivar',
      color: isDeactivating ? 'negative' : 'positive'
    }
  }).onOk(async () => {
    const clinicId = activeClinicId.value || user.value?.clinicId || DEFAULT_CLINIC_ID
    toggleLoadingId.value = targetUser.id
    try {
      const res = await api.delete(`/clinics/${clinicId}/users/${targetUser.id}`)
      targetUser.status = res.data.status
      Notify.create({
        type: 'positive',
        message: `Estado actualizado a ${getStatusLabel(res.data.status)}.`,
        position: 'bottom-right'
      })
    } catch (err) {
      console.error('Error alternando estado:', err)
      Notify.create({
        type: 'negative',
        message: err.response?.data?.detail || 'No se pudo actualizar el estado.',
        position: 'bottom-right'
      })
    } finally {
      toggleLoadingId.value = null
    }
  })
}

function confirmDisaffiliate (targetUser) {
  const roleName = targetUser.role === 'DOCTOR' ? 'el médico' : 'el paciente'

  Dialog.create({
    title: `¿Desvincular de la Sede?`,
    message: `¿Estás seguro de que deseas desvincular a ${roleName} ${targetUser.full_name || targetUser.email} de esta clínica? Como es una entidad global de la plataforma, su cuenta personal NO se cancelará ni se desactivará, y podrá seguir operando en otras clínicas.`,
    cancel: true,
    persistent: true,
    ok: {
      label: 'Desvincular',
      color: 'deep-orange-9'
    }
  }).onOk(async () => {
    const clinicId = activeClinicId.value || user.value?.clinicId || DEFAULT_CLINIC_ID
    toggleLoadingId.value = targetUser.id
    try {
      const res = await api.post(`/clinics/${clinicId}/users/${targetUser.id}/disaffiliate`)
      Notify.create({
        type: 'positive',
        message: res.data.message || 'Desvinculación exitosa.',
        position: 'bottom-right'
      })
      await fetchUsers()
    } catch (err) {
      console.error('Error desvinculando usuario:', err)
      Notify.create({
        type: 'negative',
        message: err.response?.data?.detail || 'No se pudo desvincular al usuario.',
        position: 'bottom-right'
      })
    } finally {
      toggleLoadingId.value = null
    }
  })
}

onMounted(async () => {
  await fetchClinics()
  await fetchUsers()
})
</script>
