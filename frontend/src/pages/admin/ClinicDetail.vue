<template>
  <q-page class="p-4 md:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-6xl mx-auto space-y-6">
      <!-- Breadcrumb y Botón Volver -->
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center space-x-2 text-xs text-slate-500">
          <router-link to="/admin/clinics" class="text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1">
            <q-icon name="arrow_back" size="14px" />
            Gestión de Clínicas
          </router-link>
          <span>/</span>
          <span class="text-slate-700 font-bold truncate max-w-xs">{{ clinic?.name || 'Cargando sede...' }}</span>
        </div>

        <q-btn
          outline
          color="slate-7"
          icon="arrow_back"
          label="Volver a Clínicas"
          no-caps
          size="sm"
          class="font-semibold"
          to="/admin/clinics"
        />
      </div>

      <!-- Spinner de carga -->
      <div v-if="loading" class="py-16 text-center text-slate-500">
        <q-spinner color="indigo" size="48px" />
        <p class="mt-4 text-xs font-semibold">Cargando expediente de la clínica...</p>
      </div>

      <template v-else-if="clinic">
        <!-- Banner de Encabezado de la Clínica -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div class="flex items-start space-x-4">
            <!-- Avatar / Logotipo de la Clínica -->
            <div class="relative group shrink-0">
              <div
                class="w-16 h-16 rounded-2xl flex items-center justify-center text-white shrink-0 shadow-sm overflow-hidden border border-slate-200"
                :class="clinic.logo_url ? 'bg-white' : (clinic.is_active ? 'bg-gradient-to-br from-indigo-600 to-indigo-800' : 'bg-slate-400')"
              >
                <img
                  v-if="clinic.logo_url"
                  :src="clinic.logo_url"
                  alt="Logo Clínica"
                  class="w-full h-full object-cover"
                />
                <q-icon v-else name="apartment" size="32px" />
              </div>

              <!-- Botón flotante para subir/cambiar foto -->
              <q-btn
                round
                dense
                color="indigo-7"
                icon="photo_camera"
                size="xs"
                class="absolute -bottom-1 -right-1 shadow-md border-2 border-white"
                :loading="uploadingLogo"
                @click="triggerLogoUpload"
              >
                <q-tooltip>Subir o cambiar fotografía/logo de la clínica</q-tooltip>
              </q-btn>
            </div>

            <!-- Input de archivo oculto para el logo -->
            <input
              ref="logoFileInput"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/jpg"
              class="hidden"
              @change="handleLogoFileSelected"
            />

            <div class="space-y-1">
              <div class="flex items-center gap-2 flex-wrap">
                <h1 class="text-xl font-bold text-slate-900 leading-tight">{{ clinic.name }}</h1>
                <!-- Estado Sede -->
                <span
                  class="px-2.5 py-0.5 rounded-full text-xs font-bold"
                  :class="clinic.is_active ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' : 'bg-amber-100 text-amber-900 border border-amber-200'"
                >
                  {{ clinic.is_active ? 'Sede Activa' : 'Sede Suspendida' }}
                </span>
                <!-- Badge IA -->
                <span
                  class="px-2 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1"
                  :class="clinic.ai_enabled ? 'bg-purple-100 text-purple-800 border border-purple-200' : 'bg-slate-100 text-slate-500'"
                >
                  <q-icon name="auto_awesome" size="12px" />
                  {{ clinic.ai_enabled ? `IA Activa (${clinic.ai_model || 'gpt-4o-mini'})` : 'IA Desactivada' }}
                </span>
                <!-- Badge Consulta Asistida -->
                <span
                  v-if="clinic.ai_enabled && clinic.ai_consultation_assistant_enabled"
                  class="px-2 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1 bg-teal-100 text-teal-800 border border-teal-200"
                >
                  <q-icon name="mic" size="12px" />
                  Consulta Asistida ON
                </span>
              </div>

              <div class="text-xs text-slate-500 flex flex-wrap gap-x-4 gap-y-1 pt-1">
                <span><strong>ID:</strong> <code class="font-mono text-slate-700">{{ clinic.id }}</code></span>
                <span><strong>Slug:</strong> {{ clinic.slug }}</span>
                <span><strong>Zona Horaria:</strong> {{ clinic.timezone }}</span>
                <span><strong>País:</strong> {{ clinic.country_code }}</span>
              </div>

              <div class="text-xs text-slate-600 flex flex-wrap gap-x-4 gap-y-1 pt-0.5">
                <span v-if="clinic.phone" class="flex items-center space-x-1">
                  <q-icon name="phone" size="14px" class="text-slate-400" />
                  <span>{{ clinic.phone }}</span>
                </span>
                <span v-if="clinic.address" class="flex items-center space-x-1">
                  <q-icon name="location_on" size="14px" class="text-slate-400" />
                  <span>{{ clinic.address }}</span>
                </span>
              </div>
            </div>
          </div>

          <!-- Acciones Rápidas -->
          <div class="flex items-center gap-2 self-start md:self-center flex-wrap">
            <q-btn
              outline
              color="indigo-7"
              icon="add_photo_alternate"
              label="Cambiar Logo"
              no-caps
              size="sm"
              class="font-semibold"
              :loading="uploadingLogo"
              @click="triggerLogoUpload"
            />
            <q-btn
              v-if="clinic.logo_url"
              flat
              color="negative"
              icon="delete"
              label="Quitar Logo"
              no-caps
              size="sm"
              class="font-semibold text-2xs"
              :loading="deletingLogo"
              @click="deleteLogo"
            />
            <q-btn
              :color="clinic.is_active ? 'amber-8' : 'emerald-7'"
              :icon="clinic.is_active ? 'block' : 'check_circle'"
              :label="clinic.is_active ? 'Suspender Sede' : 'Activar Sede'"
              no-caps
              size="sm"
              class="font-semibold"
              @click="toggleActiveStatus"
            />
          </div>
        </div>

        <!-- Pestañas de Navegación del Detalle -->
        <q-tabs
          v-model="activeTab"
          dense
          no-caps
          active-color="indigo-8"
          indicator-color="indigo-7"
          class="bg-white border border-slate-200 rounded-xl px-2 shadow-xs text-slate-600 font-semibold"
        >
          <q-tab name="modules" icon="tune" label="Módulos del Sistema y Licencias" />
          <q-tab name="general" icon="settings" label="Información General" />
          <q-tab name="doctors" icon="medical_services" :label="`Médicos Afiliados (${doctors.length})`" />
          <q-tab name="rooms" icon="meeting_room" :label="`Consultorios (${rooms.length})`" />
        </q-tabs>

        <!-- Panel 1: Módulos del Sistema (Activación / Inactivación) -->
        <div v-show="activeTab === 'modules'" class="space-y-6">
          <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
            <div class="flex items-center justify-between pb-4 border-b border-slate-100 flex-wrap gap-2">
              <div>
                <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
                  <q-icon name="extension" color="indigo" size="22px" />
                  Módulos y Capacidades del Sistema por Clínica
                </h2>
                <p class="text-xs text-slate-500 mt-0.5">
                  Activa o desactiva las funcionalidades. Los cambios se guardan <strong>automáticamente</strong> al activar o desactivar cada módulo.
                </p>
              </div>

              <!-- Indicador de guardado automático -->
              <transition name="fade">
                <div v-if="savingModules" class="flex items-center gap-1.5 text-indigo-700 text-xs font-semibold bg-indigo-50 border border-indigo-200 px-3 py-1.5 rounded-full shadow-xs">
                  <q-spinner size="14px" color="indigo" />
                  Guardando...
                </div>
                <div v-else-if="lastSaved" class="flex items-center gap-1.5 text-emerald-700 text-xs font-semibold bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full shadow-xs">
                  <q-icon name="check_circle" size="14px" />
                  Guardado
                </div>
              </transition>
            </div>

            <!-- Lista de Módulos con Switches -->
            <div class="grid grid-cols-1 gap-4">
              <!-- 1. Módulo Inteligencia Artificial (IA General) -->
              <div class="p-5 rounded-2xl border transition-all" :class="modulesForm.ai_assistant ? 'bg-purple-50/40 border-purple-300' : 'bg-slate-50/70 border-slate-200'">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-start space-x-3.5">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      :class="modulesForm.ai_assistant ? 'bg-purple-600 text-white' : 'bg-slate-200 text-slate-500'"
                    >
                      <q-icon name="auto_awesome" size="20px" />
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-slate-900">Inteligencia Artificial Clínica (Asistente de Redacción y Dictado)</span>
                        <span
                          class="px-2 py-0.5 rounded-full text-2xs font-bold"
                          :class="modulesForm.ai_assistant ? 'bg-purple-100 text-purple-800' : 'bg-slate-200 text-slate-600'"
                        >
                          {{ modulesForm.ai_assistant ? 'ACTIVADO' : 'INACTIVO' }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                        Permite a los médicos especialistas de esta sede utilizar el <strong>dictado por voz continuo</strong> y el botón de <strong>optimización con IA</strong> en anamnesis, examen físico, diagnóstico y plan de tratamiento.
                      </p>
                    </div>
                  </div>

                  <q-toggle
                    v-model="modulesForm.ai_assistant"
                    color="purple"
                    size="lg"
                    @update:model-value="onAiToggleChange"
                  />
                </div>

                <!-- Subformulario de configuración de IA (URL, API Key, Modelos) -->
                <div v-if="modulesForm.ai_assistant" class="mt-4 pt-4 border-t border-purple-200 space-y-3">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <q-input
                      v-model="modulesForm.ai_api_url"
                      label="URL del Endpoint de la API *"
                      placeholder="https://api.openai.com/v1/chat/completions"
                      filled
                      dense
                      hint="Compatible con APIs estilo OpenAI, Ollama o pasarelas REST"
                    />

                    <q-input
                      v-model="modulesForm.ai_api_key"
                      :label="clinic?.has_ai_key ? 'Token / API Key (Configurado - deja vacío para mantener)' : 'Token / API Key del Proveedor *'"
                      :placeholder="clinic?.has_ai_key ? '••••••••••••••••••••••••' : 'sk-proj-...'"
                      type="password"
                      filled
                      dense
                      :hint="clinic?.has_ai_key ? 'Ya existe un token guardado y cifrado.' : 'Se almacena cifrado en reposo.'"
                    />
                  </div>

                  <!-- Selector de Modelo de IA con Consulta en Vivo -->
                  <div class="p-3 bg-white rounded-xl border border-purple-200 space-y-2">
                    <div class="flex items-center justify-between">
                      <label class="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                        <q-icon name="psychology" size="16px" class="text-purple-700" />
                        Modelo de IA Seleccionado para esta Clínica *
                      </label>

                      <q-btn
                        flat
                        dense
                        no-caps
                        size="sm"
                        color="purple-8"
                        icon="sync"
                        label="Consultar Modelos del Proveedor"
                        :loading="fetchingModels"
                        class="font-semibold text-2xs"
                        @click="fetchProviderModels"
                      >
                        <q-tooltip>Conectar con el endpoint del proveedor y consultar los modelos disponibles en vivo</q-tooltip>
                      </q-btn>
                    </div>

                    <q-select
                      v-model="modulesForm.ai_model"
                      :options="filteredModels"
                      use-input
                      fill-input
                      hide-selected
                      new-value-mode="add-unique"
                      filled
                      dense
                      options-dense
                      placeholder="Seleccionar o escribir nombre de modelo (ej. gpt-4o-mini)..."
                      hint="Escoge un modelo de la lista devuelta o escribe uno personalizado."
                      @filter="filterModels"
                    />
                  </div>
                </div>
              </div>

              <!-- 2. Módulo Consulta Asistida por AI -->
              <div
                class="p-5 rounded-2xl border transition-all"
                :class="modulesForm.ai_consultation && modulesForm.ai_assistant ? 'bg-teal-50/40 border-teal-300' : 'bg-slate-50/70 border-slate-200'"
              >
                <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:1rem;">
                  <div style="display:flex; align-items:flex-start; gap:0.875rem; flex:1; min-width:0;">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      :class="modulesForm.ai_consultation && modulesForm.ai_assistant ? 'bg-teal-700 text-white' : 'bg-slate-200 text-slate-500'"
                    >
                      <q-icon name="mic" size="20px" />
                    </div>
                    <div style="flex:1; min-width:0;">
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-sm font-bold text-slate-900">Botón de "Consulta asistida por AI" (Grabación y Prellenado)</span>
                        <span
                          class="px-2 py-0.5 rounded-full text-2xs font-bold"
                          :class="modulesForm.ai_consultation && modulesForm.ai_assistant ? 'bg-teal-100 text-teal-800' : 'bg-slate-200 text-slate-600'"
                        >
                          {{ modulesForm.ai_consultation && modulesForm.ai_assistant ? 'ACTIVADO' : 'INACTIVO' }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                        Muestra el botón <strong>"Consulta asistida por AI"</strong> en la pantalla del médico durante la consulta. Permite grabar todo el diálogo médico-paciente, transcribirlo, adjuntar exámenes médicos o fotos y <strong>prellenar automáticamente anamnesis, examen físico, diagnóstico CIE-10, plan y recetas médicas</strong>.
                      </p>
                      <div v-if="!modulesForm.ai_assistant" class="mt-2 text-2xs font-semibold text-amber-700 flex items-center gap-1">
                        <q-icon name="warning" size="14px" />
                        Requiere que el módulo principal de Inteligencia Artificial esté activado.
                      </div>
                    </div>
                  </div>
                  <q-toggle
                    v-model="modulesForm.ai_consultation"
                    color="teal"
                    size="lg"
                    :disable="!modulesForm.ai_assistant"
                    @update:model-value="saveModulesConfig"
                    style="flex-shrink:0;"
                  />
                </div>
              </div>

              <!-- 3. Módulo de Urgencias y Código Azul (SOS) -->
              <div class="p-5 rounded-2xl border transition-all" :class="modulesForm.emergencies ? 'bg-rose-50/40 border-rose-300' : 'bg-slate-50/70 border-slate-200'">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-start space-x-3.5 min-w-0">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      :class="modulesForm.emergencies ? 'bg-rose-600 text-white' : 'bg-slate-200 text-slate-500'"
                    >
                      <q-icon name="emergency" size="20px" />
                    </div>
                    <div class="min-w-0">
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-sm font-bold text-slate-900">Protocolo de Urgencias y Código Azul (SOS)</span>
                        <span
                          class="px-2 py-0.5 rounded-full text-2xs font-bold"
                          :class="modulesForm.emergencies ? 'bg-rose-100 text-rose-800' : 'bg-slate-200 text-slate-600'"
                        >
                          {{ modulesForm.emergencies ? 'ACTIVADO' : 'INACTIVO' }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                        Habilita la activación de alertas de emergencia SOS para pacientes, cola prioritaria en recepción, y monitoreo en vivo en la Torre de Control con escalamiento automático a médicos de guardia.
                      </p>
                    </div>
                  </div>

                  <q-toggle
                    v-model="modulesForm.emergencies"
                    color="rose"
                    size="lg"
                    class="shrink-0"
                    @update:model-value="saveModulesConfig"
                  />
                </div>

                <!-- Configuración de Urgencias (fuera de la fila principal para no desplazar el toggle) -->
                <div v-if="modulesForm.emergencies" class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 pt-3 border-t border-rose-200">
                  <q-select
                    v-model="modulesForm.emergency_doctor_attempts"
                    :options="[2, 3, 4, 5]"
                    label="Intentos de llamado a médicos antes de escalar"
                    filled
                    dense
                    options-dense
                  />
                  <q-input
                    v-model="modulesForm.emergency_backup_phone"
                    label="Teléfono de Emergencias / Respaldo de Sede"
                    placeholder="+58 212 555-0000"
                    filled
                    dense
                  />
                </div>
              </div>

              <!-- 4. Módulo de Caja y Facturación -->
              <div class="p-5 rounded-2xl border transition-all" :class="modulesForm.cashier ? 'bg-emerald-50/40 border-emerald-300' : 'bg-slate-50/70 border-slate-200'">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-start space-x-3.5">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      :class="modulesForm.cashier ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'"
                    >
                      <q-icon name="point_of_sale" size="20px" />
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-slate-900">Módulo de Caja y Facturación (Cashier / Pagos)</span>
                        <span
                          class="px-2 py-0.5 rounded-full text-2xs font-bold"
                          :class="modulesForm.cashier ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'"
                        >
                          {{ modulesForm.cashier ? 'ACTIVADO' : 'INACTIVO' }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                        Permite a la recepción cobrar consultas médicas, procedimientos paraclínicos, registrar pagos en dólares o moneda local y emitir recibos de pago.
                      </p>
                    </div>
                  </div>

                  <q-toggle
                    v-model="modulesForm.cashier"
                    color="emerald"
                    size="lg"
                    @update:model-value="saveModulesConfig"
                  />
                </div>
              </div>

              <!-- 5. Módulo de Consultorios Físicos (Mutex Lock) -->
              <div class="p-5 rounded-2xl border transition-all" :class="modulesForm.rooms ? 'bg-blue-50/40 border-blue-300' : 'bg-slate-50/70 border-slate-200'">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-start space-x-3.5">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      :class="modulesForm.rooms ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'"
                    >
                      <q-icon name="meeting_room" size="20px" />
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-slate-900">Gestión de Consultorios Físicos y Mutex Lock</span>
                        <span
                          class="px-2 py-0.5 rounded-full text-2xs font-bold"
                          :class="modulesForm.rooms ? 'bg-blue-100 text-blue-800' : 'bg-slate-200 text-slate-600'"
                        >
                          {{ modulesForm.rooms ? 'ACTIVADO' : 'INACTIVO' }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                        Control y asignación de consultorios físicos por especialidad con bloqueo de exclusión mutua para impedir colisiones o sobre-agendamiento físico.
                      </p>
                    </div>
                  </div>

                  <q-toggle
                    v-model="modulesForm.rooms"
                    color="blue"
                    size="lg"
                    @update:model-value="saveModulesConfig"
                  />
                </div>
              </div>

              <!-- 6. Recetas Digitales y Verificación QR -->
              <div class="p-5 rounded-2xl border transition-all" :class="modulesForm.prescriptions ? 'bg-amber-50/40 border-amber-300' : 'bg-slate-50/70 border-slate-200'">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-start space-x-3.5">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      :class="modulesForm.prescriptions ? 'bg-amber-600 text-white' : 'bg-slate-200 text-slate-500'"
                    >
                      <q-icon name="medication" size="20px" />
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-slate-900">Recetas Digitales con Verificación Pública QR</span>
                        <span
                          class="px-2 py-0.5 rounded-full text-2xs font-bold"
                          :class="modulesForm.prescriptions ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-600'"
                        >
                          {{ modulesForm.prescriptions ? 'ACTIVADO' : 'INACTIVO' }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                        Generación de récipes y órdenes médicas con hash SHA-256 inmutable y enlace de verificación pública por código QR para validación en farmacias.
                      </p>
                    </div>
                  </div>

                  <q-toggle
                    v-model="modulesForm.prescriptions"
                    color="amber"
                    size="lg"
                    @update:model-value="saveModulesConfig"
                  />
                </div>
              </div>

              <!-- 7. Portal Web de Pacientes -->
              <div class="p-5 rounded-2xl border transition-all" :class="modulesForm.patient_portal ? 'bg-cyan-50/40 border-cyan-300' : 'bg-slate-50/70 border-slate-200'">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-start space-x-3.5">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      :class="modulesForm.patient_portal ? 'bg-cyan-600 text-white' : 'bg-slate-200 text-slate-500'"
                    >
                      <q-icon name="event_available" size="20px" />
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-slate-900">Portal de Pacientes y Agendamiento Online</span>
                        <span
                          class="px-2 py-0.5 rounded-full text-2xs font-bold"
                          :class="modulesForm.patient_portal ? 'bg-cyan-100 text-cyan-800' : 'bg-slate-200 text-slate-600'"
                        >
                          {{ modulesForm.patient_portal ? 'ACTIVADO' : 'INACTIVO' }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                        Permite a los pacientes registrarse y agendar consultas médicas directamente desde la web para ellos o sus dependientes familiares.
                      </p>
                    </div>
                  </div>

                  <q-toggle
                    v-model="modulesForm.patient_portal"
                    color="cyan"
                    size="lg"
                    @update:model-value="saveModulesConfig"
                  />
                </div>
              </div>

              <!-- 8. MFA Obligatorio para Recepcionistas -->
              <div class="p-5 rounded-2xl border transition-all" :class="modulesForm.require_mfa_for_receptionists ? 'bg-indigo-50/40 border-indigo-300' : 'bg-slate-50/70 border-slate-200'">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-start space-x-3.5">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      :class="modulesForm.require_mfa_for_receptionists ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-500'"
                    >
                      <q-icon name="security" size="20px" />
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-slate-900">Exigir Autenticación de Dos Factores (MFA) en Recepción</span>
                        <span
                          class="px-2 py-0.5 rounded-full text-2xs font-bold"
                          :class="modulesForm.require_mfa_for_receptionists ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-200 text-slate-600'"
                        >
                          {{ modulesForm.require_mfa_for_receptionists ? 'OBLIGATORIO' : 'OPCIONAL' }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                        Obliga a los usuarios con rol de recepción y caja a configurar Google Authenticator o TOTP para iniciar sesión en esta sede.
                      </p>
                    </div>
                  </div>

                  <q-toggle
                    v-model="modulesForm.require_mfa_for_receptionists"
                    color="indigo"
                    size="lg"
                    @update:model-value="saveModulesConfig"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Panel 2: Información General -->
        <div v-show="activeTab === 'general'" class="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
          <div>
            <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <q-icon name="edit_note" color="indigo" size="22px" />
              Parámetros y Datos Básicos de la Sede
            </h2>
            <p class="text-xs text-slate-500 mt-0.5">Identidad visual y datos de contacto de la sede clínica.</p>
          </div>

          <!-- Sección de Logotipo / Avatar / Fotografía de la Clínica -->
          <div class="p-5 bg-slate-50/80 rounded-2xl border border-slate-200 flex flex-col sm:flex-row items-center gap-5">
            <div
              class="w-24 h-24 rounded-2xl border-2 border-dashed border-indigo-300 flex items-center justify-center overflow-hidden bg-white shrink-0 shadow-xs"
            >
              <img
                v-if="clinic.logo_url"
                :src="clinic.logo_url"
                alt="Logo Clínica"
                class="w-full h-full object-cover"
              />
              <div v-else class="text-center text-slate-400 p-2">
                <q-icon name="add_photo_alternate" size="32px" class="text-indigo-400" />
                <div class="text-3xs font-semibold mt-1">Sin Foto</div>
              </div>
            </div>

            <div class="space-y-1.5 flex-1 text-center sm:text-left">
              <div class="text-sm font-bold text-slate-900">Fotografía o Logotipo de la Clínica</div>
              <p class="text-xs text-slate-600 leading-relaxed">
                Este avatar se muestra en el encabezado de la sede, en el directorio público de médicos y en las recetas médicas digitales emitidas. Formatos soportados: JPG, PNG o WEBP (máx. 5 MB).
              </p>
              <div class="flex items-center gap-2 pt-1 justify-center sm:justify-start flex-wrap">
                <q-btn
                  unelevated
                  color="indigo-7"
                  icon="upload"
                  label="Subir / Cambiar Foto"
                  no-caps
                  size="sm"
                  class="font-bold"
                  :loading="uploadingLogo"
                  @click="triggerLogoUpload"
                />
                <q-btn
                  v-if="clinic.logo_url"
                  outline
                  color="negative"
                  icon="delete"
                  label="Eliminar Foto"
                  no-caps
                  size="sm"
                  class="font-semibold"
                  :loading="deletingLogo"
                  @click="deleteLogo"
                />
              </div>
            </div>
          </div>

          <form class="space-y-4 pt-2" @submit.prevent="saveGeneralInfo">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <q-input v-model="generalForm.name" label="Nombre de la Clínica *" filled required />
              <q-input v-model="generalForm.slug" label="Slug Identificador *" filled required />
              <q-input v-model="generalForm.phone" label="Teléfono de Contacto" filled />
              <q-input v-model="generalForm.address" label="Dirección Física" filled />
              <q-input v-model="generalForm.timezone" label="Zona Horaria *" filled required />
              <q-input v-model="generalForm.country_code" label="Código de País (ISO 3166-1) *" filled maxlength="2" required />
            </div>

            <div class="flex justify-end pt-3">
              <q-btn
                type="submit"
                color="indigo-7"
                icon="save"
                label="Guardar Datos Generales"
                no-caps
                class="font-bold"
                :loading="savingGeneral"
              />
            </div>
          </form>
        </div>

        <!-- Panel 3: Médicos Afiliados -->
        <div v-show="activeTab === 'doctors'" class="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <q-icon name="medical_services" color="indigo" size="22px" />
              Médicos Afiliados a esta Sede ({{ doctors.length }})
            </h2>
          </div>

          <div v-if="doctors.length === 0" class="py-8 text-center text-slate-400 text-xs">
            No hay médicos afiliados actualmente a esta clínica.
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
              v-for="doc in doctors"
              :key="doc.id"
              class="p-4 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between gap-3 text-xs"
            >
              <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center shrink-0">
                  {{ doc.full_name?.charAt(0) || 'D' }}
                </div>
                <div>
                  <div class="font-bold text-slate-900">{{ doc.full_name }}</div>
                  <div class="text-slate-500">{{ doc.specialty || 'Medicina General' }}</div>
                  <div class="text-2xs text-slate-400 font-mono">{{ doc.email }}</div>
                </div>
              </div>
              <div class="text-right">
                <span class="px-2 py-0.5 rounded-full text-3xs font-bold bg-indigo-100 text-indigo-800">
                  {{ doc.contract_type || 'INDEPENDIENTE' }}
                </span>
                <div v-if="doc.consultation_fee" class="text-xs font-semibold text-slate-700 mt-1">
                  {{ doc.consultation_fee }} {{ doc.currency || 'USD' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Panel 4: Consultorios Físicos -->
        <div v-show="activeTab === 'rooms'" class="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <q-icon name="meeting_room" color="indigo" size="22px" />
              Consultorios y Espacios Físicos ({{ rooms.length }})
            </h2>
            <q-btn
              outline
              color="indigo"
              size="sm"
              icon="open_in_new"
              label="Gestionar Consultorios"
              no-caps
              to="/clinic/rooms"
            />
          </div>

          <div v-if="rooms.length === 0" class="py-8 text-center text-slate-400 text-xs">
            No se han registrado consultorios físicos en esta sede.
          </div>

          <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            <div
              v-for="room in rooms"
              :key="room.id"
              class="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1 text-xs"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-900">{{ room.name }}</span>
                <span class="px-2 py-0.5 rounded-full text-3xs font-bold" :class="room.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'">
                  {{ room.is_active ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
              <div v-if="room.room_number" class="text-slate-500">Número/Código: {{ room.room_number }}</div>
              <div v-if="room.specialty" class="text-indigo-600 font-semibold text-2xs">{{ room.specialty }}</div>
              <div v-if="room.description" class="text-slate-400 text-2xs italic truncate">{{ room.description }}</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()

const clinicId = ref(route.params.id)
const clinic = ref(null)
const loading = ref(true)
const activeTab = ref('modules')

// Logotipo / Avatar
const logoFileInput = ref(null)
const uploadingLogo = ref(false)
const deletingLogo = ref(false)

// Listados relacionados
const doctors = ref([])
const rooms = ref([])

// Formulario de Módulos
const modulesForm = reactive({
  ai_assistant: false,
  ai_consultation: false,
  ai_api_url: '',
  ai_api_key: '',
  ai_model: 'gpt-4o-mini',
  emergencies: true,
  emergency_doctor_attempts: 2,
  emergency_backup_phone: '',
  cashier: true,
  rooms: true,
  prescriptions: true,
  patient_portal: true,
  require_mfa_for_receptionists: false
})
const savingModules = ref(false)
const lastSaved = ref(false)
let lastSavedTimer = null

// Modelos de IA
const defaultModelOptions = [
  'gpt-4o-mini',
  'gpt-4o',
  'gpt-4-turbo',
  'gpt-3.5-turbo',
  'claude-3-5-sonnet-20240620',
  'llama-3.1-70b-versatile',
  'llama-3.1-8b-instant',
  'deepseek-chat'
]
const availableModels = ref([...defaultModelOptions])
const filteredModels = ref([...defaultModelOptions])
const fetchingModels = ref(false)

// Formulario de Información General
const generalForm = reactive({
  name: '',
  slug: '',
  phone: '',
  address: '',
  timezone: 'America/Caracas',
  country_code: 'VE'
})
const savingGeneral = ref(false)

function onAiToggleChange (val) {
  if (!val) {
    modulesForm.ai_consultation = false
  }
  saveModulesConfig()
}

function filterModels (val, update) {
  if (val === '') {
    update(() => {
      filteredModels.value = availableModels.value
    })
    return
  }
  update(() => {
    const needle = val.toLowerCase()
    filteredModels.value = availableModels.value.filter(
      v => v.toLowerCase().indexOf(needle) > -1
    )
  })
}

async function fetchProviderModels () {
  if (!modulesForm.ai_api_url) {
    $q.notify({
      type: 'warning',
      message: 'Ingresa la URL del Endpoint de la API antes de consultar modelos.',
      position: 'top'
    })
    return
  }

  if (!modulesForm.ai_api_key && !clinic.value?.has_ai_key) {
    $q.notify({
      type: 'warning',
      message: 'Ingresa el Token / API Key para autenticar la consulta con el proveedor.',
      position: 'top'
    })
    return
  }

  fetchingModels.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.post(
      '/clinics/query-ai-models',
      {
        clinic_id: clinicId.value,
        ai_api_url: modulesForm.ai_api_url,
        ai_api_key: modulesForm.ai_api_key || null
      },
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )

    if (data.models && data.models.length > 0) {
      availableModels.value = data.models
      filteredModels.value = data.models
      if (modulesForm.ai_model && !availableModels.value.includes(modulesForm.ai_model)) {
        availableModels.value.unshift(modulesForm.ai_model)
      } else if (!modulesForm.ai_model) {
        modulesForm.ai_model = data.models[0]
      }
      $q.notify({
        type: 'positive',
        message: `Se encontraron ${data.models.length} modelos en el proveedor.`,
        position: 'top'
      })
    }
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudieron consultar los modelos del proveedor.',
      position: 'top'
    })
  } finally {
    fetchingModels.value = false
  }
}

async function loadClinicData () {
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const authHeader = { headers: { Authorization: `Bearer ${token}` } }

    const { data } = await api.get(`/clinics/${clinicId.value}`, authHeader)
    clinic.value = data

    // Sincronizar formulario de módulos
    const activeMods = data.active_modules || {}
    modulesForm.ai_assistant = !!data.ai_enabled
    modulesForm.ai_consultation = !!data.ai_consultation_assistant_enabled
    modulesForm.ai_api_url = data.ai_api_url || 'https://api.openai.com/v1/chat/completions'
    modulesForm.ai_api_key = ''
    modulesForm.ai_model = data.ai_model || 'gpt-4o-mini'

    modulesForm.emergencies = activeMods.emergencies !== false
    modulesForm.emergency_doctor_attempts = data.emergency_doctor_attempts || 2
    modulesForm.emergency_backup_phone = data.emergency_backup_phone || ''
    modulesForm.cashier = activeMods.cashier !== false
    modulesForm.rooms = activeMods.rooms !== false
    modulesForm.prescriptions = activeMods.prescriptions !== false
    modulesForm.patient_portal = activeMods.patient_portal !== false
    modulesForm.require_mfa_for_receptionists = !!data.require_mfa_for_receptionists

    // Pre-poblar selector de modelos
    const preset = [
      data.ai_model || 'gpt-4o-mini',
      ...defaultModelOptions
    ].filter((v, i, a) => a.indexOf(v) === i)
    availableModels.value = preset
    filteredModels.value = [...preset]

    // Sincronizar formulario general
    generalForm.name = data.name || ''
    generalForm.slug = data.slug || ''
    generalForm.phone = data.phone || ''
    generalForm.address = data.address || ''
    generalForm.timezone = data.timezone || 'America/Caracas'
    generalForm.country_code = data.country_code || 'VE'

    // Cargar médicos y consultorios en paralelo
    loadRelatedData(authHeader)
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al cargar la información de la clínica.',
      position: 'top'
    })
    router.push('/admin/clinics')
  } finally {
    loading.value = false
  }
}

async function loadRelatedData (authHeader) {
  try {
    const [docsRes, roomsRes] = await Promise.allSettled([
      api.get(`/clinics/${clinicId.value}/doctors`, authHeader),
      api.get(`/rooms/clinics/${clinicId.value}/rooms`, authHeader)
    ])
    if (docsRes.status === 'fulfilled') {
      doctors.value = docsRes.value.data || []
    }
    if (roomsRes.status === 'fulfilled') {
      rooms.value = roomsRes.value.data || []
    }
  } catch (err) {
    console.warn('Error cargando doctores o consultorios:', err)
  }
}

async function saveModulesConfig () {
  savingModules.value = true
  lastSaved.value = false
  if (lastSavedTimer) clearTimeout(lastSavedTimer)
  try {
    const token = localStorage.getItem('access_token')
    const payload = {
      ai_enabled: modulesForm.ai_assistant,
      ai_consultation_assistant_enabled: modulesForm.ai_assistant ? modulesForm.ai_consultation : false,
      ai_api_url: modulesForm.ai_api_url || null,
      ai_api_key: modulesForm.ai_api_key || undefined,
      ai_model: modulesForm.ai_model || 'gpt-4o-mini',
      require_mfa_for_receptionists: modulesForm.require_mfa_for_receptionists,
      emergency_doctor_attempts: modulesForm.emergency_doctor_attempts,
      emergency_backup_phone: modulesForm.emergency_backup_phone || null,
      modules: {
        ai_assistant: modulesForm.ai_assistant,
        ai_consultation: modulesForm.ai_assistant ? modulesForm.ai_consultation : false,
        emergencies: modulesForm.emergencies,
        cashier: modulesForm.cashier,
        rooms: modulesForm.rooms,
        prescriptions: modulesForm.prescriptions,
        patient_portal: modulesForm.patient_portal,
        require_mfa_for_receptionists: modulesForm.require_mfa_for_receptionists
      }
    }

    const { data } = await api.put(
      `/clinics/${clinicId.value}/modules`,
      payload,
      { headers: { Authorization: `Bearer ${token}` } }
    )

    clinic.value = data
    lastSaved.value = true
    lastSavedTimer = setTimeout(() => { lastSaved.value = false }, 2500)
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al guardar la configuración de módulos.',
      position: 'top'
    })
  } finally {
    savingModules.value = false
  }
}

async function saveGeneralInfo () {
  savingGeneral.value = true
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.put(
      `/clinics/${clinicId.value}`,
      {
        name: generalForm.name,
        slug: generalForm.slug,
        phone: generalForm.phone || null,
        address: generalForm.address || null,
        timezone: generalForm.timezone,
        country_code: generalForm.country_code
      },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    clinic.value = data
    $q.notify({
      type: 'positive',
      message: 'Datos generales de la clínica actualizados con éxito.',
      position: 'top'
    })
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al actualizar los datos generales.',
      position: 'top'
    })
  } finally {
    savingGeneral.value = false
  }
}

async function toggleActiveStatus () {
  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.patch(
      `/clinics/${clinicId.value}/toggle-active`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    )
    clinic.value = data
    $q.notify({
      type: 'positive',
      message: `Clínica ${data.is_active ? 'activada' : 'suspendida'} correctamente.`,
      position: 'top'
    })
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudo cambiar el estado de la clínica.',
      position: 'top'
    })
  }
}

function triggerLogoUpload () {
  logoFileInput.value?.click()
}

async function handleLogoFileSelected (e) {
  const file = e.target.files?.[0]
  if (!file) return

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
  if (!allowedTypes.includes(file.type)) {
    $q.notify({
      type: 'warning',
      message: 'Formato no admitido. Selecciona una imagen JPG, PNG o WEBP.',
      position: 'top'
    })
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    $q.notify({
      type: 'warning',
      message: 'La imagen seleccionada supera el límite máximo de 5 MB.',
      position: 'top'
    })
    return
  }

  uploadingLogo.value = true
  try {
    const token = localStorage.getItem('access_token')
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await api.post(
      `/clinics/${clinicId.value}/logo`,
      formData,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    clinic.value = data
    $q.notify({
      type: 'positive',
      message: 'Logotipo de la clínica actualizado correctamente.',
      position: 'top'
    })
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al subir la imagen del logo.',
      position: 'top'
    })
  } finally {
    uploadingLogo.value = false
    if (logoFileInput.value) logoFileInput.value.value = ''
  }
}

async function deleteLogo () {
  $q.dialog({
    title: 'Confirmar Eliminación',
    message: '¿Estás seguro de que deseas eliminar el logotipo de la clínica? Se restaurará el icono por defecto.',
    cancel: { label: 'Cancelar', flat: true },
    ok: { label: 'Eliminar', color: 'negative' }
  }).onOk(async () => {
    deletingLogo.value = true
    try {
      const token = localStorage.getItem('access_token')
      const { data } = await api.delete(
        `/clinics/${clinicId.value}/logo`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      clinic.value = data
      $q.notify({
        type: 'positive',
        message: 'Logotipo eliminado correctamente.',
        position: 'top'
      })
    } catch (err) {
      $q.notify({
        type: 'negative',
        message: err.response?.data?.detail || 'Error al eliminar el logotipo.',
        position: 'top'
      })
    } finally {
      deletingLogo.value = false
    }
  })
}

onMounted(() => {
  loadClinicData()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.35s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
