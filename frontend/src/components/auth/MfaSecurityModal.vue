<template>
  <q-dialog v-model="isOpen" persistent>
    <q-card class="w-full max-w-md rounded-2xl bg-white shadow-2xl overflow-hidden border border-slate-200">
      <!-- Cabecera del modal -->
      <div class="bg-gradient-to-r from-teal-700 to-teal-800 text-white p-5 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
            <q-icon name="security" size="22px" />
          </div>
          <div>
            <h3 class="text-base font-bold leading-tight m-0">Verificación en Dos Pasos (MFA)</h3>
            <p class="text-xs text-teal-100/90 m-0">Google Authenticator y Apps TOTP</p>
          </div>
        </div>
        <q-btn icon="close" flat round dense text-color="white" v-close-popup />
      </div>

      <q-card-section class="p-6 space-y-5">
        <!-- Estado de Carga Inicial -->
        <div v-if="loadingStatus" class="py-10 text-center space-y-3">
          <q-spinner-dots color="teal" size="40px" />
          <p class="text-xs text-slate-500">Comprobando estado de seguridad de tu cuenta...</p>
        </div>

        <!-- Caso 1: MFA ya está Activo -->
        <div v-else-if="mfaEnabled && !settingUp" class="space-y-5">
          <div class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
            <q-icon name="verified_user" color="emerald-7" size="28px" class="shrink-0 mt-0.5" />
            <div class="space-y-1">
              <div class="text-sm font-bold text-emerald-900">
                Segundo Factor (MFA) Activado
              </div>
              <p class="text-xs text-emerald-700 leading-relaxed m-0">
                Tu cuenta está protegida. Al iniciar sesión se solicitará un código temporal de 6 dígitos generado por tu aplicación Google Authenticator.
              </p>
            </div>
          </div>

          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-2">
            <div class="flex items-center gap-2 font-bold text-slate-800">
              <q-icon name="smartphone" size="16px" color="teal" />
              <span>Aplicación Vinculada</span>
            </div>
            <p class="m-0 text-slate-500">
              Compatible con Google Authenticator, Microsoft Authenticator, Authy o cualquier app compatible con RFC 6238 TOTP.
            </p>
          </div>

          <!-- Formulario para desactivar MFA si el usuario lo desea -->
          <div v-if="showDisableForm" class="p-4 rounded-xl bg-rose-50 border border-rose-200 space-y-3">
            <div class="text-xs font-bold text-rose-900">
              Confirmar Desactivación de Seguridad
            </div>
            <p class="text-2xs text-rose-700 m-0">
              Por tu seguridad, ingresa tu contraseña actual para confirmar la desactivación del segundo factor:
            </p>
            <q-input
              v-model="disablePassword"
              type="password"
              placeholder="Tu contraseña actual"
              outlined
              dense
              class="bg-white rounded-xl"
              :error="!!disableError"
              :error-message="disableError"
            />
            <div class="flex items-center justify-end gap-2">
              <q-btn
                flat
                label="Cancelar"
                no-caps
                size="sm"
                color="slate-7"
                @click="cancelDisable"
              />
              <q-btn
                unelevated
                label="Confirmar y Desactivar"
                no-caps
                size="sm"
                color="rose-7"
                text-color="white"
                :loading="disabling"
                @click="confirmDisableMfa"
              />
            </div>
          </div>

          <div v-else class="flex justify-between items-center pt-2">
            <q-btn
              outline
              color="rose-7"
              label="Desactivar Segundo Factor"
              icon="lock_open"
              no-caps
              size="sm"
              class="font-bold rounded-xl"
              @click="showDisableForm = true"
            />
            <q-btn
              unelevated
              color="teal-8"
              label="Entendido"
              no-caps
              size="sm"
              class="font-bold rounded-xl px-4"
              v-close-popup
            />
          </div>
        </div>

        <!-- Caso 2: MFA no está activo y NO ha iniciado el proceso de setup -->
        <div v-else-if="!mfaEnabled && !settingUp" class="space-y-4">
          <div class="text-center space-y-2 py-2">
            <div class="w-14 h-14 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center mx-auto shadow-xs border border-teal-100">
              <q-icon name="phonelink_lock" size="30px" />
            </div>
            <h4 class="text-base font-black text-slate-800 m-0">
              Protege tu cuenta con Google Authenticator
            </h4>
            <p class="text-xs text-slate-500 leading-relaxed m-0">
              Añade una capa de seguridad extra. Cada vez que inicies sesión se te pedirá un código de 6 dígitos que solo tú podrás ver desde tu teléfono móvil.
            </p>
          </div>

          <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-2">
            <div class="font-bold text-slate-800 flex items-center gap-1.5">
              <q-icon name="check_circle" size="16px" color="teal" />
              <span>¿Cómo funciona?</span>
            </div>
            <ol class="list-decimal pl-4 space-y-1 m-0 text-2xs text-slate-500">
              <li>Instala Google Authenticator en tu celular (Android o iPhone).</li>
              <li>Escanea el código QR que generaremos para tu cuenta.</li>
              <li>Ingresa el código de confirmación de 6 dígitos y listo.</li>
            </ol>
          </div>

          <div class="pt-2">
            <q-btn
              unelevated
              color="teal-8"
              label="Configurar Google Authenticator"
              icon="qr_code_scanner"
              no-caps
              class="full-width py-2.5 rounded-xl font-bold text-white shadow-md shadow-teal-800/20"
              :loading="startingSetup"
              @click="startMfaSetup"
            />
          </div>
        </div>

        <!-- Caso 3: Proceso de Setup en marcha (Mostrando QR y campo de verificación) -->
        <div v-else class="space-y-4">
          <div class="text-center space-y-1">
            <div class="text-xs font-bold text-teal-800 uppercase tracking-wider">
              Paso 1 de 2: Escanea el Código QR
            </div>
            <p class="text-2xs text-slate-500 m-0">
              Abre Google Authenticator, presiona el botón <span class="font-bold">+</span> y selecciona <span class="font-bold">Escanear código QR</span>.
            </p>
          </div>

          <!-- Imagen del QR generada en base64 -->
          <div class="flex flex-col items-center justify-center p-3 bg-slate-50 rounded-2xl border border-slate-200">
            <div class="bg-white p-2.5 rounded-xl shadow-xs border border-slate-100">
              <img
                :src="setupData.qr_code"
                alt="Código QR de Google Authenticator"
                class="w-44 h-44 object-contain rounded-lg block mx-auto"
              />
            </div>

            <!-- Clave de configuración manual -->
            <div class="mt-3 text-center w-full">
              <div class="text-3xs text-slate-400 font-bold uppercase tracking-wider mb-1">
                ¿No puedes escanear? Ingresa esta clave manualmente:
              </div>
              <div class="flex items-center justify-center gap-1.5 bg-white px-3 py-1.5 rounded-lg border border-slate-200 max-w-xs mx-auto">
                <span class="font-mono font-bold text-xs text-slate-800 tracking-wider select-all">
                  {{ setupData.secret }}
                </span>
                <q-btn
                  flat
                  round
                  dense
                  size="xs"
                  icon="content_copy"
                  color="teal"
                  @click="copySecretKey"
                >
                  <q-tooltip>Copiar clave secreta</q-tooltip>
                </q-btn>
              </div>
            </div>
          </div>

          <!-- Paso 2: Validación del código inicial -->
          <div class="space-y-2 pt-1">
            <div class="text-xs font-bold text-slate-700">
              Paso 2 de 2: Ingresa el código de 6 dígitos que muestra tu app
            </div>
            <q-input
              v-model="verificationCode"
              type="text"
              mask="######"
              placeholder="000000"
              outlined
              dense
              class="rounded-xl font-mono text-center tracking-widest text-lg font-bold bg-white"
              autofocus
              :error="!!enableError"
              :error-message="enableError"
              @keyup.enter="confirmEnableMfa"
            >
              <template v-slot:prepend>
                <q-icon name="pin" size="18px" color="teal" />
              </template>
            </q-input>
          </div>

          <div class="flex items-center justify-between pt-2">
            <q-btn
              flat
              label="Atrás"
              no-caps
              size="sm"
              color="slate-7"
              @click="settingUp = false"
            />
            <q-btn
              unelevated
              color="teal-8"
              label="Verificar y Activar MFA"
              icon-right="verified"
              no-caps
              size="sm"
              class="font-bold rounded-xl px-4 text-white shadow-md shadow-teal-800/20"
              :loading="enabling"
              :disable="cleanVerificationCode.length !== 6"
              @click="confirmEnableMfa"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from 'boot/axios'
import { copyToClipboard, useQuasar } from 'quasar'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'status-changed'])

const $q = useQuasar()

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loadingStatus = ref(false)
const mfaEnabled = ref(false)
const settingUp = ref(false)
const startingSetup = ref(false)
const enabling = ref(false)
const enableError = ref('')
const setupData = ref({
  secret: '',
  otpauth_url: '',
  qr_code: ''
})
const verificationCode = ref('')

const showDisableForm = ref(false)
const disablePassword = ref('')
const disableError = ref('')
const disabling = ref(false)

const cleanVerificationCode = computed(() => {
  return (verificationCode.value || '').replace(/\D/g, '')
})

watch(isOpen, (val) => {
  if (val) {
    fetchMfaStatus()
    settingUp.value = false
    showDisableForm.value = false
    disablePassword.value = ''
    disableError.value = ''
    verificationCode.value = ''
    enableError.value = ''
  }
})

async function fetchMfaStatus () {
  loadingStatus.value = true
  try {
    const { data } = await api.get('/auth/mfa/status')
    mfaEnabled.value = !!data.mfa_enabled
    emit('status-changed', mfaEnabled.value)
  } catch (err) {
    console.error('Error obteniendo estado de MFA:', err)
  } finally {
    loadingStatus.value = false
  }
}

async function startMfaSetup () {
  startingSetup.value = true
  enableError.value = ''
  verificationCode.value = ''
  try {
    const { data } = await api.post('/auth/mfa/setup')
    setupData.value = data
    settingUp.value = true
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudo iniciar la configuración de MFA.'
    })
  } finally {
    startingSetup.value = false
  }
}

async function copySecretKey () {
  try {
    await copyToClipboard(setupData.value.secret)
    $q.notify({
      type: 'positive',
      message: 'Clave secreta copiada al portapapeles',
      timeout: 1500
    })
  } catch (e) {
    console.error(e)
  }
}

async function confirmEnableMfa () {
  if (cleanVerificationCode.value.length !== 6) {
    enableError.value = 'El código debe contener exactamente 6 dígitos.'
    return
  }

  enabling.value = true
  enableError.value = ''

  try {
    await api.post('/auth/mfa/enable', {
      secret: setupData.value.secret,
      code: cleanVerificationCode.value
    })

    $q.notify({
      type: 'positive',
      message: '¡Segundo factor (Google Authenticator) activado exitosamente!',
      icon: 'verified'
    })

    mfaEnabled.value = true
    settingUp.value = false
    emit('status-changed', true)
  } catch (err) {
    enableError.value = err.response?.data?.detail || 'Código de verificación incorrecto o expirado.'
  } finally {
    enabling.value = false
  }
}

function cancelDisable () {
  showDisableForm.value = false
  disablePassword.value = ''
  disableError.value = ''
}

async function confirmDisableMfa () {
  if (!disablePassword.value) {
    disableError.value = 'Ingresa tu contraseña para continuar.'
    return
  }

  disabling.value = true
  disableError.value = ''

  try {
    await api.post('/auth/mfa/disable', {
      password: disablePassword.value
    })

    $q.notify({
      type: 'info',
      message: 'Autenticación de segundo factor desactivada.',
      icon: 'lock_open'
    })

    mfaEnabled.value = false
    showDisableForm.value = false
    disablePassword.value = ''
    emit('status-changed', false)
  } catch (err) {
    disableError.value = err.response?.data?.detail || 'Contraseña incorrecta.'
  } finally {
    disabling.value = false
  }
}
</script>
