<template>
  <q-page class="p-4 sm:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-5xl mx-auto space-y-6">
      <!-- 1. Encabezado Principal de Configuración -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center space-x-4">
          <!-- Avatar del usuario con indicativo de rol -->
          <div class="relative">
            <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-teal-700 to-teal-500 text-white flex items-center justify-center font-bold text-xl shadow-md overflow-hidden border-2 border-white ring-2 ring-teal-100">
              <img
                v-if="userProfile.profile_picture_url && !avatarLoadError"
                :src="resolvedAvatarUrl"
                class="w-full h-full object-cover"
                alt="Foto de perfil"
                @error="avatarLoadError = true"
              />
              <span v-else>{{ getInitials(userProfile.full_name || userProfile.email) }}</span>
            </div>
          </div>

          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="text-xl font-black text-slate-900 leading-tight m-0">
                {{ userProfile.full_name || userProfile.email || 'Mi Cuenta' }}
              </h1>
              <q-badge :color="getRoleBadgeColor(userProfile.role)" class="text-2xs font-bold px-2 py-0.5 rounded-full uppercase">
                {{ formatRole(userProfile.role) }}
              </q-badge>
              <q-badge v-if="userProfile.mfa_enabled" color="positive" class="text-2xs font-bold px-2 py-0.5 rounded-full">
                <q-icon name="verified_user" size="11px" class="mr-1" /> MFA Activo
              </q-badge>
            </div>
            <p class="text-xs text-slate-500 mt-1 m-0">
              Configuración de cuenta, seguridad de acceso, métodos de recuperación, alertas y privacidad.
            </p>
          </div>
        </div>

        <!-- Botón de acción rápida para recargar -->
        <div class="flex items-center gap-2 self-end sm:self-center">
          <q-btn
            flat
            dense
            round
            icon="refresh"
            color="teal-8"
            :loading="loadingProfile"
            @click="fetchAllData"
          >
            <q-tooltip>Actualizar datos</q-tooltip>
          </q-btn>
        </div>
      </div>

      <!-- 2. Navegación por Pestañas -->
      <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <q-tabs
          v-model="activeTab"
          dense
          class="text-slate-600 border-b border-slate-200 bg-slate-50/50"
          active-color="teal"
          indicator-color="teal"
          align="justify"
          narrow-indicator
        >
          <q-tab name="profile" icon="person" label="Perfil & Avatar" no-caps class="text-xs font-bold py-3" />
          <q-tab name="security" icon="lock" label="Contraseña & Recuperación" no-caps class="text-xs font-bold py-3" />
          <q-tab name="mfa_sessions" icon="devices" label="Doble Factor & Sesiones" no-caps class="text-xs font-bold py-3" />
          <q-tab name="notifications" icon="notifications" label="Alertas & Notificaciones" no-caps class="text-xs font-bold py-3" />
          <q-tab name="privacy" icon="privacy_tip" label="Privacidad & Datos (RGPD)" no-caps class="text-xs font-bold py-3 text-slate-700" />
        </q-tabs>

        <q-tab-panels v-model="activeTab" animated class="p-6">
          <!-- ========================================== -->
          <!-- PESTAÑA 1: PERFIL & FOTO DE PERFIL / AVATAR -->
          <!-- ========================================== -->
          <q-tab-panel name="profile" class="p-0 space-y-6">
            <div>
              <h2 class="text-base font-bold text-slate-900 m-0">Información Personal & Fotografía de Perfil</h2>
              <p class="text-xs text-slate-500 m-0 mt-0.5">
                Actualiza los datos con los que te identificas dentro del sistema clínico y directorio institucional.
              </p>
            </div>

            <!-- Sección de Avatar -->
            <div class="p-5 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-center gap-6">
              <div class="relative shrink-0">
                <div class="w-24 h-24 rounded-2xl bg-gradient-to-tr from-teal-700 to-teal-500 text-white flex items-center justify-center font-bold text-3xl shadow-md overflow-hidden border-2 border-white ring-2 ring-teal-100">
                  <img
                    v-if="userProfile.profile_picture_url && !avatarLoadError"
                    :src="resolvedAvatarUrl"
                    class="w-full h-full object-cover"
                    alt="Avatar de usuario"
                    @error="avatarLoadError = true"
                  />
                  <span v-else>{{ getInitials(userProfile.full_name || userProfile.email) }}</span>
                </div>
                <div v-if="uploadingAvatar" class="absolute inset-0 bg-black/60 rounded-2xl flex items-center justify-center">
                  <q-spinner color="white" size="28px" />
                </div>
              </div>

              <div class="space-y-2 text-center sm:text-left flex-1">
                <div class="font-bold text-slate-800 text-sm">Foto o Avatar de Perfil</div>
                <p class="text-xs text-slate-500 m-0 leading-relaxed max-w-lg">
                  Formatos permitidos: JPG, PNG o WEBP. Tamaño máximo 5 MB. Tu fotografía se optimiza automáticamente y se eliminan metadatos EXIF por tu seguridad y privacidad.
                </p>
                <div class="flex items-center gap-2 justify-center sm:justify-start pt-1">
                  <input
                    ref="avatarInputRef"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    class="hidden"
                    @change="handleAvatarFileSelect"
                  />
                  <q-btn
                    unelevated
                    color="primary"
                    icon="photo_camera"
                    label="Subir Fotografía"
                    no-caps
                    size="sm"
                    class="font-bold rounded-xl px-3 py-1.5"
                    :loading="uploadingAvatar"
                    @click="triggerAvatarUpload"
                  />
                  <q-btn
                    v-if="userProfile.profile_picture_url"
                    flat
                    color="negative"
                    icon="delete"
                    label="Quitar Foto"
                    no-caps
                    size="sm"
                    class="font-bold rounded-xl px-3 py-1.5"
                    :loading="deletingAvatar"
                    @click="deleteAvatar"
                  />
                </div>
              </div>
            </div>

            <!-- Formulario de Datos Básicos -->
            <form class="space-y-4" @submit.prevent="saveProfile">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-bold text-slate-700 mb-1">Nombre</label>
                  <q-input
                    v-model="profileForm.first_name"
                    outlined
                    dense
                    placeholder="Ej. Ana"
                    class="bg-white"
                  >
                    <template #prepend>
                      <q-icon name="badge" size="18px" color="teal" />
                    </template>
                  </q-input>
                </div>

                <div>
                  <label class="block text-xs font-bold text-slate-700 mb-1">Apellido</label>
                  <q-input
                    v-model="profileForm.last_name"
                    outlined
                    dense
                    placeholder="Ej. Gómez"
                    class="bg-white"
                  >
                    <template #prepend>
                      <q-icon name="badge" size="18px" color="teal" />
                    </template>
                  </q-input>
                </div>

                <div>
                  <label class="block text-xs font-bold text-slate-700 mb-1">Correo Electrónico Principal</label>
                  <q-input
                    v-model="profileForm.email"
                    type="email"
                    outlined
                    dense
                    placeholder="usuario@dominio.com"
                    class="bg-white"
                  >
                    <template #prepend>
                      <q-icon name="email" size="18px" color="teal" />
                    </template>
                  </q-input>
                </div>

                <div>
                  <label class="block text-xs font-bold text-slate-700 mb-1">Teléfono Principal</label>
                  <q-input
                    v-model="profileForm.phone"
                    outlined
                    dense
                    placeholder="+58 412 1234567"
                    class="bg-white"
                  >
                    <template #prepend>
                      <q-icon name="phone" size="18px" color="teal" />
                    </template>
                  </q-input>
                </div>
              </div>

              <div class="flex justify-end pt-3">
                <q-btn
                  type="submit"
                  unelevated
                  color="primary"
                  icon="save"
                  label="Guardar Datos de Perfil"
                  no-caps
                  class="font-bold rounded-xl px-5 py-2 text-xs shadow-sm"
                  :loading="savingProfile"
                />
              </div>
            </form>
          </q-tab-panel>

          <!-- ========================================== -->
          <!-- PESTAÑA 2: SEGURIDAD & RECUPERACIÓN        -->
          <!-- ========================================== -->
          <q-tab-panel name="security" class="p-0 space-y-8">
            <!-- Bloque 1: Cambio de Contraseña -->
            <div class="space-y-4">
              <div class="border-b border-slate-100 pb-2">
                <h2 class="text-base font-bold text-slate-900 m-0">Actualizar Contraseña de Acceso</h2>
                <p class="text-xs text-slate-500 m-0 mt-0.5">
                  Recomendamos utilizar una contraseña robusta con al menos 8 caracteres, números y símbolos.
                </p>
              </div>

              <form class="space-y-4 max-w-xl" @submit.prevent="submitChangePassword">
                <div>
                  <label class="block text-xs font-bold text-slate-700 mb-1">Contraseña Actual</label>
                  <q-input
                    v-model="passwordForm.current_password"
                    :type="showCurrentPass ? 'text' : 'password'"
                    outlined
                    dense
                    class="bg-white"
                    placeholder="Tu contraseña actual"
                  >
                    <template #append>
                      <q-icon
                        :name="showCurrentPass ? 'visibility_off' : 'visibility'"
                        class="cursor-pointer"
                        @click="showCurrentPass = !showCurrentPass"
                      />
                    </template>
                  </q-input>
                </div>

                <div>
                  <label class="block text-xs font-bold text-slate-700 mb-1">Nueva Contraseña</label>
                  <q-input
                    v-model="passwordForm.new_password"
                    :type="showNewPass ? 'text' : 'password'"
                    outlined
                    dense
                    class="bg-white"
                    placeholder="Mínimo 8 caracteres"
                  >
                    <template #append>
                      <q-icon
                        :name="showNewPass ? 'visibility_off' : 'visibility'"
                        class="cursor-pointer"
                        @click="showNewPass = !showNewPass"
                      />
                    </template>
                  </q-input>
                  <!-- Indicador visual de fortaleza -->
                  <div v-if="passwordForm.new_password" class="mt-2 space-y-1">
                    <div class="flex items-center justify-between text-2xs font-semibold">
                      <span class="text-slate-500">Fortaleza:</span>
                      <span :class="passwordStrength.colorClass">{{ passwordStrength.label }}</span>
                    </div>
                    <q-linear-progress
                      :value="passwordStrength.score"
                      :color="passwordStrength.color"
                      rounded
                      class="h-1.5"
                    />
                  </div>
                </div>

                <div>
                  <label class="block text-xs font-bold text-slate-700 mb-1">Confirmar Nueva Contraseña</label>
                  <q-input
                    v-model="passwordForm.confirm_password"
                    :type="showNewPass ? 'text' : 'password'"
                    outlined
                    dense
                    class="bg-white"
                    placeholder="Repite la nueva contraseña"
                    :error="passwordMismatch"
                    error-message="Las contraseñas no coinciden"
                  />
                </div>

                <q-btn
                  type="submit"
                  unelevated
                  color="teal-8"
                  icon="lock_reset"
                  label="Cambiar Contraseña"
                  no-caps
                  class="font-bold rounded-xl px-5 py-2 text-xs"
                  :loading="changingPassword"
                />
              </form>
            </div>

            <!-- Bloque 2: Métodos de Recuperación -->
            <div class="space-y-4 pt-4 border-t border-slate-200">
              <div class="border-b border-slate-100 pb-2">
                <h2 class="text-base font-bold text-slate-900 m-0">Canales de Recuperación de Cuenta</h2>
                <p class="text-xs text-slate-500 m-0 mt-0.5">
                  Establece un correo o teléfono secundario para recuperar el control de tu cuenta si pierdes el acceso a tu canal principal.
                </p>
              </div>

              <form class="space-y-4 max-w-xl" @submit.prevent="saveRecoveryMethods">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-bold text-slate-700 mb-1">Correo Secundario / Respaldo</label>
                    <q-input
                      v-model="recoveryForm.recovery_email"
                      type="email"
                      outlined
                      dense
                      placeholder="respaldo@example.com"
                      class="bg-white"
                    >
                      <template #prepend>
                        <q-icon name="mark_email_read" size="18px" color="teal" />
                      </template>
                    </q-input>
                  </div>

                  <div>
                    <label class="block text-xs font-bold text-slate-700 mb-1">Teléfono de Recuperación</label>
                    <q-input
                      v-model="recoveryForm.recovery_phone"
                      outlined
                      dense
                      placeholder="+58 414 0000000"
                      class="bg-white"
                    >
                      <template #prepend>
                        <q-icon name="contact_phone" size="18px" color="teal" />
                      </template>
                    </q-input>
                  </div>
                </div>

                <q-btn
                  type="submit"
                  unelevated
                  color="primary"
                  icon="save"
                  label="Guardar Canales de Respaldo"
                  no-caps
                  class="font-bold rounded-xl px-5 py-2 text-xs"
                  :loading="savingRecovery"
                />
              </form>
            </div>

            <!-- Bloque 3: Códigos de Respaldo de Emergencia (Backup Codes) -->
            <div class="space-y-4 pt-4 border-t border-slate-200">
              <div class="border-b border-slate-100 pb-2">
                <h2 class="text-base font-bold text-slate-900 m-0">Códigos de Respaldo de Emergencia (Backup Codes)</h2>
                <p class="text-xs text-slate-500 m-0 mt-0.5">
                  Claves de uso único que te permiten iniciar sesión si pierdes tu teléfono móvil o aplicación de autenticación TOTP.
                </p>
              </div>

              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div class="flex items-center space-x-3">
                  <div class="w-10 h-10 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold">
                    <q-icon name="vpn_key" size="20px" />
                  </div>
                  <div>
                    <div class="text-xs font-bold text-slate-800">
                      {{ recoveryData.has_recovery_codes ? 'Códigos de respaldo configurados (' + recoveryData.recovery_codes_count + ' disponibles)' : 'Sin códigos de respaldo activos' }}
                    </div>
                    <div class="text-2xs text-slate-500 mt-0.5">
                      Genera 8 códigos imprimibles para conservarlos en una libreta o caja fuerte.
                    </div>
                  </div>
                </div>

                <q-btn
                  outline
                  color="teal-8"
                  icon="pin"
                  label="Generar Nuevos Códigos"
                  no-caps
                  size="sm"
                  class="font-bold rounded-xl px-4 py-2 shrink-0"
                  :loading="generatingCodes"
                  @click="generateBackupCodes"
                />
              </div>
            </div>
          </q-tab-panel>

          <!-- ========================================== -->
          <!-- PESTAÑA 3: DOBLE FACTOR (MFA) & SESIONES    -->
          <!-- ========================================== -->
          <q-tab-panel name="mfa_sessions" class="p-0 space-y-8">
            <!-- Sección MFA -->
            <div class="space-y-4">
              <div class="border-b border-slate-100 pb-2">
                <h2 class="text-base font-bold text-slate-900 m-0">Autenticación en Dos Pasos (Google Authenticator)</h2>
                <p class="text-xs text-slate-500 m-0 mt-0.5">
                  Añade una capa de protección adicional solicitando un código temporal de 6 dígitos al iniciar sesión.
                </p>
              </div>

              <!-- Banner Estado MFA -->
              <div
                class="p-5 rounded-2xl border flex flex-col sm:flex-row items-center justify-between gap-4"
                :class="userProfile.mfa_enabled ? 'bg-emerald-50/70 border-emerald-300' : 'bg-amber-50/60 border-amber-200'"
              >
                <div class="flex items-center space-x-3.5">
                  <div
                    class="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold shadow-xs shrink-0"
                    :class="userProfile.mfa_enabled ? 'bg-emerald-600' : 'bg-amber-600'"
                  >
                    <q-icon :name="userProfile.mfa_enabled ? 'verified_user' : 'security'" size="26px" />
                  </div>
                  <div>
                    <h3 class="text-sm font-bold m-0" :class="userProfile.mfa_enabled ? 'text-emerald-950' : 'text-amber-950'">
                      {{ userProfile.mfa_enabled ? 'Autenticación de Dos Factores Activa' : 'Autenticación de Dos Factores Desactivada' }}
                    </h3>
                    <p class="text-xs m-0 mt-0.5" :class="userProfile.mfa_enabled ? 'text-emerald-700' : 'text-amber-700'">
                      {{ userProfile.mfa_enabled ? 'Tu cuenta está protegida con Google Authenticator o aplicación TOTP compatible.' : 'Recomendamos activar MFA para proteger tu información médica e identidad institucional.' }}
                    </p>
                  </div>
                </div>

                <div class="shrink-0 flex items-center gap-2">
                  <q-btn
                    v-if="!userProfile.mfa_enabled"
                    unelevated
                    color="positive"
                    icon="add_moderator"
                    label="Activar MFA Ahora"
                    no-caps
                    size="sm"
                    class="font-bold rounded-xl px-4 py-2"
                    @click="openMfaModal"
                  />
                  <q-btn
                    v-else
                    outline
                    color="negative"
                    icon="lock_open"
                    label="Desactivar MFA"
                    no-caps
                    size="sm"
                    class="font-bold rounded-xl px-4 py-2"
                    @click="openMfaModal"
                  />
                </div>
              </div>
            </div>

            <!-- Sección Sesiones Activas -->
            <div class="space-y-4 pt-4 border-t border-slate-200">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-2">
                <div>
                  <h2 class="text-base font-bold text-slate-900 m-0">Dispositivos & Sesiones Activas</h2>
                  <p class="text-xs text-slate-500 m-0 mt-0.5">
                    Revisa los dispositivos que han iniciado sesión recientemente en tu cuenta y desconecta los no reconocidos.
                  </p>
                </div>
                <q-btn
                  v-if="sessionsList.length > 1"
                  outline
                  color="negative"
                  icon="logout"
                  label="Cerrar las demás sesiones"
                  no-caps
                  size="xs"
                  class="font-bold rounded-xl px-3 py-1.5 self-start sm:self-auto"
                  :loading="revokingAllSessions"
                  @click="revokeAllOtherSessions"
                />
              </div>

              <!-- Lista de Sesiones -->
              <div v-if="loadingSessions" class="text-center py-8">
                <q-spinner-dots color="teal" size="36px" />
                <p class="text-xs text-slate-500 mt-2">Cargando dispositivos activos...</p>
              </div>

              <div v-else-if="!sessionsList.length" class="p-6 text-center text-slate-400 bg-slate-50 rounded-2xl border border-slate-200">
                <q-icon name="devices" size="36px" class="opacity-40 mb-2" />
                <p class="text-xs m-0">No se encontraron otras sesiones registradas.</p>
              </div>

              <div v-else class="space-y-3">
                <div
                  v-for="ses in sessionsList"
                  :key="ses.id"
                  class="p-4 rounded-xl border flex items-center justify-between gap-4 transition-all"
                  :class="ses.is_current ? 'bg-teal-50/50 border-teal-300' : 'bg-white border-slate-200'"
                >
                  <div class="flex items-center space-x-3.5">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shadow-xs shrink-0"
                      :class="ses.is_current ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-600'"
                    >
                      <q-icon :name="getDeviceIcon(ses.device_info)" size="20px" />
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-xs font-bold text-slate-900">
                          {{ formatDeviceInfo(ses.device_info) }}
                        </span>
                        <q-badge v-if="ses.is_current" color="teal" class="text-3xs font-bold px-1.5 py-0.5 rounded-full">
                          Esta Sesión
                        </q-badge>
                      </div>
                      <div class="text-2xs text-slate-500 mt-0.5 flex items-center gap-2 flex-wrap">
                        <span v-if="ses.ip_address">IP: {{ ses.ip_address }}</span>
                        <span v-if="ses.issued_at">• Iniciada {{ formatDate(ses.issued_at) }}</span>
                      </div>
                    </div>
                  </div>

                  <q-btn
                    v-if="!ses.is_current"
                    flat
                    round
                    dense
                    icon="cancel"
                    color="negative"
                    @click="revokeSession(ses.id)"
                  >
                    <q-tooltip>Cerrar sesión en este dispositivo</q-tooltip>
                  </q-btn>
                </div>
              </div>
            </div>
          </q-tab-panel>

          <!-- ========================================== -->
          <!-- PESTAÑA 4: ALERTAS & NOTIFICACIONES        -->
          <!-- ========================================== -->
          <q-tab-panel name="notifications" class="p-0 space-y-6">
            <div class="border-b border-slate-100 pb-2">
              <h2 class="text-base font-bold text-slate-900 m-0">Preferencia de Alertas Multicanal</h2>
              <p class="text-xs text-slate-500 m-0 mt-0.5">
                Configura con precisión qué notificaciones deseas recibir a través de Correo Electrónico, Notificaciones Push y WhatsApp.
              </p>
            </div>

            <!-- Canales Globales Habilitados -->
            <div class="space-y-3">
              <div class="text-xs font-bold text-slate-800 uppercase tracking-wider">
                1. Canales Principales Activos
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div
                  class="p-4 rounded-xl border flex items-center justify-between cursor-pointer transition-all"
                  :class="selectedChannels.includes('PUSH') ? 'bg-indigo-50/60 border-indigo-300' : 'bg-slate-50 border-slate-200'"
                  @click="toggleChannel('PUSH')"
                >
                  <div class="flex items-center space-x-2.5">
                    <div class="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center">
                      <q-icon name="smartphone" size="18px" />
                    </div>
                    <div>
                      <div class="text-xs font-bold text-slate-800">Push (Web/App)</div>
                      <div class="text-3xs text-slate-500">Alertas en tiempo real</div>
                    </div>
                  </div>
                  <q-checkbox v-model="selectedChannels" val="PUSH" color="indigo" dense />
                </div>

                <div
                  class="p-4 rounded-xl border flex items-center justify-between cursor-pointer transition-all"
                  :class="selectedChannels.includes('WHATSAPP') ? 'bg-emerald-50/60 border-emerald-300' : 'bg-slate-50 border-slate-200'"
                  @click="toggleChannel('WHATSAPP')"
                >
                  <div class="flex items-center space-x-2.5">
                    <div class="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center">
                      <q-icon name="chat" size="18px" />
                    </div>
                    <div>
                      <div class="text-xs font-bold text-slate-800">WhatsApp</div>
                      <div class="text-3xs text-slate-500">Avisos y confirmaciones</div>
                    </div>
                  </div>
                  <q-checkbox v-model="selectedChannels" val="WHATSAPP" color="positive" dense />
                </div>

                <div
                  class="p-4 rounded-xl border flex items-center justify-between cursor-pointer transition-all"
                  :class="selectedChannels.includes('EMAIL') ? 'bg-teal-50/60 border-teal-300' : 'bg-slate-50 border-slate-200'"
                  @click="toggleChannel('EMAIL')"
                >
                  <div class="flex items-center space-x-2.5">
                    <div class="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center">
                      <q-icon name="mail" size="18px" />
                    </div>
                    <div>
                      <div class="text-xs font-bold text-slate-800">Correo Electrónico</div>
                      <div class="text-3xs text-slate-500">Resumen y recetas QR</div>
                    </div>
                  </div>
                  <q-checkbox v-model="selectedChannels" val="EMAIL" color="primary" dense />
                </div>
              </div>
            </div>

            <!-- Matriz Granular por Categorías -->
            <div class="space-y-3 pt-3">
              <div class="text-xs font-bold text-slate-800 uppercase tracking-wider">
                2. Configuración Granular por Categoría
              </div>

              <div class="overflow-x-auto rounded-xl border border-slate-200">
                <table class="w-full text-left text-xs">
                  <thead class="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                    <tr>
                      <th class="p-3.5">Categoría de Evento</th>
                      <th class="p-3.5 text-center w-28">Correo</th>
                      <th class="p-3.5 text-center w-28">Push</th>
                      <th class="p-3.5 text-center w-28">WhatsApp</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100 bg-white">
                    <!-- Citas Médicas -->
                    <tr>
                      <td class="p-3.5">
                        <div class="font-bold text-slate-800">Citas Médicas & Recordatorios</div>
                        <div class="text-2xs text-slate-500">Confirmación de agendamiento, recordatorio 24h antes y reprogramaciones.</div>
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.appointments.email" color="teal" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.appointments.push" color="indigo" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.appointments.whatsapp" color="positive" dense />
                      </td>
                    </tr>

                    <!-- Urgencias Médicas y SOS -->
                    <tr>
                      <td class="p-3.5">
                        <div class="font-bold text-slate-800">Urgencias Médicas & Botón SOS</div>
                        <div class="text-2xs text-slate-500">Alertas críticas de emergencia, guardia y escalamiento inmediato.</div>
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.emergencies.email" color="teal" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.emergencies.push" color="indigo" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.emergencies.whatsapp" color="positive" dense />
                      </td>
                    </tr>

                    <!-- Resultados Clínicos y Recetas -->
                    <tr>
                      <td class="p-3.5">
                        <div class="font-bold text-slate-800">Recetas Digitales & Historia Clínica</div>
                        <div class="text-2xs text-slate-500">Disponibilidad de informes médicos y recetas verificables con código QR.</div>
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.clinical_records.email" color="teal" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.clinical_records.push" color="indigo" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.clinical_records.whatsapp" color="positive" dense />
                      </td>
                    </tr>

                    <!-- Seguridad y Cuenta -->
                    <tr>
                      <td class="p-3.5">
                        <div class="font-bold text-slate-800">Seguridad & Nuevos Inicios de Sesión</div>
                        <div class="text-2xs text-slate-500">Cambios de contraseña, dispositivos desconocidos y advertencias de inicio.</div>
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.security.email" color="teal" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.security.push" color="indigo" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.security.whatsapp" color="positive" dense />
                      </td>
                    </tr>

                    <!-- Comunicados Institucionales -->
                    <tr>
                      <td class="p-3.5">
                        <div class="font-bold text-slate-800">Avisos Institucionales & Novedades Clínicas</div>
                        <div class="text-2xs text-slate-500">Boletines de salud, nuevos servicios de la clínica y mantenimiento del sistema.</div>
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.announcements.email" color="teal" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.announcements.push" color="indigo" dense />
                      </td>
                      <td class="p-3.5 text-center">
                        <q-toggle v-model="alertCategories.announcements.whatsapp" color="positive" dense />
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="flex justify-end pt-3">
              <q-btn
                unelevated
                color="primary"
                icon="save"
                label="Guardar Configuración de Alertas"
                no-caps
                class="font-bold rounded-xl px-5 py-2 text-xs shadow-sm"
                :loading="savingAlerts"
                @click="saveNotificationSettings"
              />
            </div>
          </q-tab-panel>

          <!-- ========================================== -->
          <!-- PESTAÑA 5: PRIVACIDAD & DATOS (RGPD / GDPR)-->
          <!-- ========================================== -->
          <q-tab-panel name="privacy" class="p-0 space-y-8">
            <!-- Bloque 1: Exportación y Portabilidad -->
            <div class="space-y-4">
              <div class="border-b border-slate-100 pb-2">
                <h2 class="text-base font-bold text-slate-900 m-0">Portabilidad de Datos Personales (RGPD / GDPR)</h2>
                <p class="text-xs text-slate-500 m-0 mt-0.5">
                  Conforme al Reglamento General de Protección de Datos (RGPD Art. 20), puedes obtener una copia descargable de tu información personal y registros asociados.
                </p>
              </div>

              <div class="p-5 rounded-2xl bg-teal-50/60 border border-teal-200 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div class="flex items-center space-x-3.5">
                  <div class="w-10 h-10 rounded-xl bg-teal-700 text-white flex items-center justify-center font-bold shrink-0">
                    <q-icon name="file_download" size="22px" />
                  </div>
                  <div>
                    <div class="text-xs font-bold text-teal-950">Descargar Copia de Mis Datos</div>
                    <div class="text-2xs text-teal-800/80 mt-0.5">
                      Genera un archivo comprimido JSON que incluye tu perfil, dependientes, citas, consentimientos y registros de seguridad.
                    </div>
                  </div>
                </div>

                <q-btn
                  unelevated
                  color="teal-8"
                  icon="download"
                  label="Exportar Datos (JSON)"
                  no-caps
                  size="sm"
                  class="font-bold rounded-xl px-4 py-2 shrink-0 shadow-xs"
                  :loading="exportingData"
                  @click="exportPersonalData"
                />
              </div>
            </div>

            <!-- Bloque 2: Eliminación Definitiva de la Cuenta -->
            <div class="space-y-4 pt-4 border-t border-slate-200">
              <div class="border-b border-slate-100 pb-2">
                <h2 class="text-base font-bold text-rose-900 m-0">Zona Peligrosa: Eliminación de Cuenta (Derecho al Olvido)</h2>
                <p class="text-xs text-slate-500 m-0 mt-0.5">
                  Solicitud formal de eliminación definitiva de tu usuario conforme a normativas de privacidad y RGPD Art. 17.
                </p>
              </div>

              <div class="p-5 rounded-2xl bg-rose-50/80 border border-rose-200 space-y-4">
                <div class="flex items-start gap-3">
                  <q-icon name="warning" color="negative" size="24px" class="shrink-0 mt-0.5" />
                  <div class="space-y-1 text-xs text-rose-900">
                    <div class="font-bold">Esta acción es permanente e irreversible</div>
                    <p class="m-0 leading-relaxed text-rose-800">
                      Al proceder, se cerrarán inmediatamente todas tus sesiones activas, se eliminarán tus tokens de notificación y se anonimizarán de manera definitiva tus datos personales (correo, teléfono, nombre y avatar) en nuestros sistemas.
                    </p>
                  </div>
                </div>

                <div class="flex justify-end pt-2">
                  <q-btn
                    unelevated
                    color="negative"
                    icon="delete_forever"
                    label="Eliminar mi cuenta definitivamente"
                    no-caps
                    size="sm"
                    class="font-bold rounded-xl px-4 py-2"
                    @click="showDeleteAccountModal = true"
                  />
                </div>
              </div>
            </div>
          </q-tab-panel>
        </q-tab-panels>
      </div>
    </div>

    <!-- DIÁLOGO: Códigos de Respaldo Generados -->
    <q-dialog v-model="showCodesModal" persistent>
      <q-card class="w-full max-w-md rounded-2xl p-6 bg-white space-y-4">
        <div class="flex items-center space-x-3 text-teal-800">
          <q-icon name="vpn_key" size="24px" />
          <h3 class="text-base font-bold m-0">Códigos de Respaldo de Emergencia</h3>
        </div>

        <p class="text-xs text-slate-600 leading-relaxed m-0">
          Guarda estos códigos en un lugar seguro y confidencial. Cada código puede utilizarse una única vez en caso de perder acceso a tu dispositivo principal:
        </p>

        <div class="grid grid-cols-2 gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs text-slate-900 font-bold text-center">
          <div v-for="(code, idx) in generatedCodes" :key="idx" class="p-2 bg-white rounded-lg border border-slate-100 shadow-2xs">
            {{ code }}
          </div>
        </div>

        <div class="flex items-center justify-between pt-2">
          <q-btn
            flat
            dense
            icon="copy_all"
            label="Copiar"
            color="teal-8"
            no-caps
            size="sm"
            class="font-bold"
            @click="copyBackupCodes"
          />
          <q-btn
            outline
            dense
            icon="download"
            label="Descargar .txt"
            color="primary"
            no-caps
            size="sm"
            class="font-bold px-3 py-1 rounded-lg"
            @click="downloadBackupCodes"
          />
          <q-btn
            unelevated
            label="Entendido"
            color="teal-8"
            no-caps
            size="sm"
            class="font-bold px-4 py-1.5 rounded-lg"
            v-close-popup
          />
        </div>
      </q-card>
    </q-dialog>

    <!-- DIÁLOGO: Confirmación de Eliminación Definitiva de Cuenta -->
    <q-dialog v-model="showDeleteAccountModal" persistent>
      <q-card class="w-full max-w-md rounded-2xl p-6 bg-white space-y-4 border border-rose-200">
        <div class="flex items-center space-x-3 text-rose-900">
          <div class="w-10 h-10 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center font-bold shrink-0">
            <q-icon name="delete_forever" size="22px" />
          </div>
          <div>
            <h3 class="text-base font-bold m-0 leading-tight">Confirmar Eliminación</h3>
            <p class="text-2xs text-rose-700 m-0">Derecho al Olvido & RGPD</p>
          </div>
        </div>

        <div class="text-xs text-slate-600 space-y-2 leading-relaxed">
          <p class="m-0">
            Por favor, confirma tu identidad ingresando tu contraseña actual para autorizar la baja permanente de tu cuenta:
          </p>
          <q-input
            v-model="deleteForm.password"
            type="password"
            outlined
            dense
            placeholder="Tu contraseña actual"
            class="bg-white"
          />

          <p class="text-2xs text-slate-500 m-0 mt-2">
            Motivo opcional de la baja:
          </p>
          <q-input
            v-model="deleteForm.reason"
            outlined
            dense
            placeholder="Motivo de tu salida (opcional)"
            class="bg-white text-xs"
          />
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
          <q-btn
            flat
            label="Cancelar"
            no-caps
            size="sm"
            color="slate-6"
            v-close-popup
          />
          <q-btn
            unelevated
            label="Eliminar Definitivamente"
            color="negative"
            no-caps
            size="sm"
            class="font-bold rounded-xl px-4 py-2"
            :loading="deletingAccount"
            @click="confirmDeleteAccount"
          />
        </div>
      </q-card>
    </q-dialog>

    <!-- Modal Reutilizable de MFA -->
    <MfaSecurityModal v-model="showMfaModal" @mfa-changed="fetchAllData" />
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import { clearAuthToken } from 'src/composables/useAcl'
import MfaSecurityModal from 'src/components/auth/MfaSecurityModal.vue'

const router = useRouter()
const $q = useQuasar()

const activeTab = ref('profile')
const loadingProfile = ref(false)
const savingProfile = ref(false)
const avatarLoadError = ref(false)
const uploadingAvatar = ref(false)
const deletingAvatar = ref(false)
const avatarInputRef = ref(null)

// Datos del Perfil
const userProfile = reactive({
  id: '',
  email: '',
  full_name: '',
  phone: '',
  role: 'PATIENT',
  status: 'ACTIVE',
  profile_picture_url: null,
  mfa_enabled: false,
  recovery_email: '',
  recovery_phone: '',
  preferred_notification_channels: ['PUSH', 'WHATSAPP', 'EMAIL']
})

const profileForm = reactive({
  first_name: '',
  last_name: '',
  email: '',
  phone: ''
})

// Seguridad & Contraseña
const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})
const showCurrentPass = ref(false)
const showNewPass = ref(false)
const changingPassword = ref(false)

const passwordMismatch = computed(() => {
  return !!passwordForm.confirm_password && passwordForm.new_password !== passwordForm.confirm_password
})

const passwordStrength = computed(() => {
  const p = passwordForm.new_password || ''
  if (!p) return { score: 0, label: 'Vacía', color: 'grey', colorClass: 'text-slate-400' }
  let score = 0
  if (p.length >= 8) score += 0.25
  if (p.length >= 12) score += 0.15
  if (/[a-z]/.test(p)) score += 0.15
  if (/[A-Z]/.test(p)) score += 0.15
  if (/[0-9]/.test(p)) score += 0.15
  if (/[^a-zA-Z0-9]/.test(p)) score += 0.15
  score = Math.min(1, score)

  if (score < 0.4) return { score, label: 'Débil', color: 'negative', colorClass: 'text-rose-600' }
  if (score < 0.75) return { score, label: 'Media', color: 'warning', colorClass: 'text-amber-600' }
  return { score, label: 'Fuerte', color: 'positive', colorClass: 'text-emerald-600' }
})

// Métodos de Recuperación
const recoveryForm = reactive({
  recovery_email: '',
  recovery_phone: ''
})
const savingRecovery = ref(false)
const recoveryData = reactive({
  has_recovery_codes: false,
  recovery_codes_count: 0
})
const generatingCodes = ref(false)
const showCodesModal = ref(false)
const generatedCodes = ref([])

// MFA & Sesiones
const showMfaModal = ref(false)
const sessionsList = ref([])
const loadingSessions = ref(false)
const revokingAllSessions = ref(false)

// Notificaciones Granulares
const selectedChannels = ref(['PUSH', 'WHATSAPP', 'EMAIL'])
const alertCategories = reactive({
  appointments: { email: true, push: true, whatsapp: true },
  emergencies: { email: true, push: true, whatsapp: true },
  clinical_records: { email: true, push: true, whatsapp: false },
  security: { email: true, push: true, whatsapp: false },
  announcements: { email: true, push: false, whatsapp: false }
})
const savingAlerts = ref(false)

// Privacidad & Eliminación
const exportingData = ref(false)
const showDeleteAccountModal = ref(false)
const deletingAccount = ref(false)
const deleteForm = reactive({
  password: '',
  reason: ''
})

const resolvedAvatarUrl = computed(() => {
  if (!userProfile.profile_picture_url) return ''
  const url = userProfile.profile_picture_url
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  const base = api.defaults.baseURL || ''
  return `${base.replace(/\/api\/v1\/?$/, '')}${url}`
})

function getInitials (nameOrEmail) {
  if (!nameOrEmail) return 'U'
  const parts = nameOrEmail.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return nameOrEmail.substring(0, 2).toUpperCase()
}

function formatRole (role) {
  const map = {
    SUPERADMIN: 'Super Administrador',
    CLINIC_ADMIN: 'Administrador de Sede',
    DOCTOR: 'Médico Especialista',
    RECEPTIONIST: 'Recepcionista',
    COMPLIANCE_REVIEWER: 'Cumplimiento',
    PATIENT: 'Paciente Titular'
  }
  return map[role] || role || 'Usuario'
}

function getRoleBadgeColor (role) {
  const map = {
    SUPERADMIN: 'indigo-8',
    CLINIC_ADMIN: 'cyan-9',
    DOCTOR: 'teal-8',
    RECEPTIONIST: 'purple-8',
    COMPLIANCE_REVIEWER: 'deep-orange-8',
    PATIENT: 'teal-7'
  }
  return map[role] || 'slate-6'
}

function formatDate (iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

function getDeviceIcon (ua) {
  if (!ua) return 'devices'
  const lower = ua.toLowerCase()
  if (lower.includes('mobile') || lower.includes('android') || lower.includes('iphone')) return 'smartphone'
  if (lower.includes('ipad') || lower.includes('tablet')) return 'tablet'
  return 'laptop_mac'
}

function formatDeviceInfo (ua) {
  if (!ua) return 'Dispositivo desconocido'
  if (ua.includes('iPhone')) return 'Apple iPhone (Safari)'
  if (ua.includes('Android')) return 'Dispositivo Android'
  if (ua.includes('Macintosh')) return 'Mac OS (Escritorio)'
  if (ua.includes('Windows')) return 'Windows PC (Escritorio)'
  if (ua.includes('Linux')) return 'Linux (Escritorio)'
  return ua.substring(0, 45)
}

function toggleChannel (ch) {
  const idx = selectedChannels.value.indexOf(ch)
  if (idx > -1) {
    if (selectedChannels.value.length === 1) {
      $q.notify({ type: 'warning', message: 'Debes mantener al menos un canal activo.' })
      return
    }
    selectedChannels.value.splice(idx, 1)
  } else {
    selectedChannels.value.push(ch)
  }
}

// Carga de Datos
async function fetchAllData () {
  loadingProfile.value = true
  try {
    const { data: me } = await api.get('/auth/me')
    Object.assign(userProfile, me)

    // Formulario de perfil
    if (me.full_name) {
      const parts = me.full_name.trim().split(' ')
      profileForm.first_name = parts[0] || ''
      profileForm.last_name = parts.slice(1).join(' ') || ''
    }
    profileForm.email = me.email || ''
    profileForm.phone = me.phone || ''

    // Métodos de recuperación
    fetchRecoveryMethods()
    // Sesiones
    fetchSessions()
    // Alertas
    fetchNotificationSettings()
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error cargando información del perfil.' })
  } finally {
    loadingProfile.value = false
  }
}

async function fetchRecoveryMethods () {
  try {
    const { data } = await api.get('/auth/recovery-methods')
    recoveryForm.recovery_email = data.recovery_email || ''
    recoveryForm.recovery_phone = data.recovery_phone || ''
    recoveryData.has_recovery_codes = !!data.has_recovery_codes
    recoveryData.recovery_codes_count = data.recovery_codes_count || 0
  } catch (e) {
    console.error('Error al consultar métodos de recuperación', e)
  }
}

async function fetchSessions () {
  loadingSessions.value = true
  try {
    const { data } = await api.get('/auth/sessions')
    sessionsList.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error('Error al consultar sesiones', e)
  } finally {
    loadingSessions.value = false
  }
}

async function fetchNotificationSettings () {
  try {
    const { data } = await api.get('/auth/notification-settings')
    if (Array.isArray(data.channels) && data.channels.length) {
      selectedChannels.value = data.channels
    }
    if (data.categories) {
      Object.assign(alertCategories, data.categories)
    }
  } catch (e) {
    console.error('Error al consultar configuración de notificaciones', e)
  }
}

// Acciones de Perfil
async function saveProfile () {
  savingProfile.value = true
  try {
    const payload = {
      first_name: profileForm.first_name,
      last_name: profileForm.last_name,
      email: profileForm.email,
      phone: profileForm.phone
    }
    const { data } = await api.put('/auth/me', payload)
    Object.assign(userProfile, data)
    $q.notify({ type: 'positive', message: 'Perfil actualizado exitosamente.' })
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al actualizar datos de perfil.'
    })
  } finally {
    savingProfile.value = false
  }
}

function triggerAvatarUpload () {
  if (avatarInputRef.value) avatarInputRef.value.click()
}

async function handleAvatarFileSelect (event) {
  const file = event.target.files?.[0]
  if (!file) return

  if (file.size > 5 * 1024 * 1024) {
    $q.notify({ type: 'negative', message: 'La imagen excede el límite permitido de 5 MB.' })
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  uploadingAvatar.value = true
  avatarLoadError.value = false
  try {
    const { data } = await api.post('/auth/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    userProfile.profile_picture_url = data.profile_picture_url
    $q.notify({ type: 'positive', message: '¡Foto de perfil actualizada correctamente!' })
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al subir la fotografía.'
    })
  } finally {
    uploadingAvatar.value = false
    if (avatarInputRef.value) avatarInputRef.value.value = ''
  }
}

async function deleteAvatar () {
  deletingAvatar.value = true
  try {
    await api.delete('/auth/me/avatar')
    userProfile.profile_picture_url = null
    avatarLoadError.value = false
    $q.notify({ type: 'positive', message: 'Fotografía de perfil eliminada.' })
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error al eliminar la fotografía de perfil.' })
  } finally {
    deletingAvatar.value = false
  }
}

// Acciones de Seguridad
async function submitChangePassword () {
  if (passwordMismatch.value) {
    $q.notify({ type: 'warning', message: 'Las nuevas contraseñas no coinciden.' })
    return
  }
  if (!passwordForm.new_password || passwordForm.new_password.length < 8) {
    $q.notify({ type: 'warning', message: 'La nueva contraseña debe tener al menos 8 caracteres.' })
    return
  }

  changingPassword.value = true
  try {
    await api.post('/auth/change-password', {
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password
    })
    passwordForm.current_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    $q.notify({ type: 'positive', message: '¡Contraseña actualizada correctamente!' })
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al cambiar la contraseña.'
    })
  } finally {
    changingPassword.value = false
  }
}

async function saveRecoveryMethods () {
  savingRecovery.value = true
  try {
    const { data } = await api.put('/auth/recovery-methods', {
      recovery_email: recoveryForm.recovery_email || null,
      recovery_phone: recoveryForm.recovery_phone || null
    })
    recoveryData.has_recovery_codes = data.has_recovery_codes
    recoveryData.recovery_codes_count = data.recovery_codes_count
    $q.notify({ type: 'positive', message: 'Métodos de recuperación guardados.' })
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al guardar métodos de recuperación.'
    })
  } finally {
    savingRecovery.value = false
  }
}

async function generateBackupCodes () {
  generatingCodes.value = true
  try {
    const { data } = await api.post('/auth/recovery-codes/generate')
    generatedCodes.value = data.codes || []
    recoveryData.has_recovery_codes = true
    recoveryData.recovery_codes_count = generatedCodes.value.length
    showCodesModal.value = true
    $q.notify({ type: 'positive', message: '¡Códigos de respaldo generados!' })
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error al generar códigos de respaldo.' })
  } finally {
    generatingCodes.value = false
  }
}

function copyBackupCodes () {
  const text = generatedCodes.value.join('\n')
  navigator.clipboard.writeText(text)
  $q.notify({ type: 'positive', message: 'Códigos copiados al portapapeles.' })
}

function downloadBackupCodes () {
  const content = `=== VITARECORD - CODIGOS DE RESPALDO DE EMERGENCIA ===\nFecha: ${new Date().toISOString()}\nUsuario: ${userProfile.email}\n\nCada código solo puede usarse una vez:\n\n${generatedCodes.value.join('\n')}\n`
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `vitarecord_codigos_respaldo_${userProfile.email.split('@')[0]}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

function openMfaModal () {
  showMfaModal.value = true
}

async function revokeSession (sessionId) {
  try {
    await api.delete(`/auth/sessions/${sessionId}`)
    sessionsList.value = sessionsList.value.filter(s => s.id !== sessionId)
    $q.notify({ type: 'positive', message: 'Sesión revocada exitosamente.' })
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error al revocar la sesión.' })
  }
}

async function revokeAllOtherSessions () {
  revokingAllSessions.value = true
  try {
    await api.delete('/auth/sessions')
    await fetchSessions()
    $q.notify({ type: 'positive', message: 'Todas las demás sesiones han sido cerradas.' })
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error al revocar las sesiones.' })
  } finally {
    revokingAllSessions.value = false
  }
}

// Guardar Alertas Granulares
async function saveNotificationSettings () {
  savingAlerts.value = true
  try {
    const payload = {
      channels: selectedChannels.value,
      categories: alertCategories
    }
    await api.put('/auth/notification-settings', payload)
    $q.notify({ type: 'positive', message: 'Preferencias de alertas actualizadas con éxito.' })
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error al guardar preferencias de notificación.' })
  } finally {
    savingAlerts.value = false
  }
}

// Exportación y Eliminación (RGPD / GDPR)
async function exportPersonalData () {
  exportingData.value = true
  try {
    const response = await api.get('/auth/me/export', { responseType: 'blob' })
    const blob = new Blob([response.data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vitarecord_datos_usuario_${userProfile.id.slice(0, 8)}.json`
    a.click()
    URL.revokeObjectURL(url)
    $q.notify({ type: 'positive', message: '¡Archivo de datos personales descargado!' })
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Error al exportar los datos personales.' })
  } finally {
    exportingData.value = false
  }
}

async function confirmDeleteAccount () {
  if (!deleteForm.password) {
    $q.notify({ type: 'warning', message: 'Debes ingresar tu contraseña para autorizar la eliminación.' })
    return
  }

  deletingAccount.value = true
  try {
    const { data } = await api.post('/auth/me/delete-account', {
      password: deleteForm.password,
      reason: deleteForm.reason || undefined
    })

    showDeleteAccountModal.value = false
    $q.notify({
      type: 'positive',
      message: data.message || 'Cuenta eliminada y anonimizada conforme al RGPD.',
      timeout: 5000
    })

    // Limpiar sesión y redirigir
    clearAuthToken()
    router.push({ name: 'patient-login' })
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al procesar la eliminación de la cuenta.'
    })
  } finally {
    deletingAccount.value = false
  }
}

onMounted(() => {
  fetchAllData()
})
</script>
