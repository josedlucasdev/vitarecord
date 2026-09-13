<template>
  <q-dialog v-model="isOpen">
    <q-card class="w-full max-w-md p-6 rounded-2xl bg-white shadow-xl space-y-5">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center font-bold">
            <q-icon name="notifications_active" size="20px" />
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900">Canales de Notificación</h3>
            <p class="text-xs text-slate-500">Elige cómo deseas recibir avisos y recordatorios</p>
          </div>
        </div>
        <q-btn flat round dense icon="close" v-close-popup text-color="grey-6" />
      </div>

      <!-- State: Loading -->
      <div v-if="loading" class="flex justify-center p-8">
        <q-spinner-dots color="teal" size="40px" />
      </div>

      <!-- Form Content -->
      <div v-else class="space-y-4">
        <div class="text-xs text-slate-600 leading-relaxed">
          Selecciona tus canales preferidos para confirmaciones de citas, propuestas médicas y avisos programados:
        </div>

        <div class="space-y-2.5">
          <!-- Push FCM -->
          <div
            class="flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer"
            :class="selectedChannels.includes('PUSH') ? 'bg-indigo-50/50 border-indigo-300' : 'bg-slate-50 border-slate-200'"
            @click="toggleChannel('PUSH')"
          >
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-xs">
                <q-icon name="smartphone" size="18px" />
              </div>
              <div>
                <p class="text-xs font-bold text-slate-800 m-0">Notificaciones Push (Firebase FCM)</p>
                <p class="text-[11px] text-slate-500 m-0">Alertas directas a la app móvil y navegador web</p>
              </div>
            </div>
            <q-checkbox
              v-model="selectedChannels"
              val="PUSH"
              color="indigo"
              dense
            />
          </div>

          <!-- WhatsApp -->
          <div
            class="flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer"
            :class="selectedChannels.includes('WHATSAPP') ? 'bg-emerald-50/50 border-emerald-300' : 'bg-slate-50 border-slate-200'"
            @click="toggleChannel('WHATSAPP')"
          >
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 rounded-lg bg-emerald-500 text-white flex items-center justify-center shadow-xs">
                <q-icon name="chat" size="18px" />
              </div>
              <div>
                <p class="text-xs font-bold text-slate-800 m-0">WhatsApp (Interactivo)</p>
                <p class="text-[11px] text-slate-500 m-0">Botones directos para Aceptar o Rechazar citas</p>
              </div>
            </div>
            <q-checkbox
              v-model="selectedChannels"
              val="WHATSAPP"
              color="positive"
              dense
            />
          </div>

          <!-- Email -->
          <div
            class="flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer"
            :class="selectedChannels.includes('EMAIL') ? 'bg-teal-50/50 border-teal-300' : 'bg-slate-50 border-slate-200'"
            @click="toggleChannel('EMAIL')"
          >
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center shadow-xs">
                <q-icon name="mail" size="18px" />
              </div>
              <div>
                <p class="text-xs font-bold text-slate-800 m-0">Correo Electrónico</p>
                <p class="text-[11px] text-slate-500 m-0">Resumen detallado institucional y recetas digitales</p>
              </div>
            </div>
            <q-checkbox
              v-model="selectedChannels"
              val="EMAIL"
              color="primary"
              dense
            />
          </div>

          <!-- SMS -->
          <div
            class="flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer"
            :class="selectedChannels.includes('SMS') ? 'bg-blue-50/50 border-blue-300' : 'bg-slate-50 border-slate-200'"
            @click="toggleChannel('SMS')"
          >
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-xs">
                <q-icon name="sms" size="18px" />
              </div>
              <div>
                <p class="text-xs font-bold text-slate-800 m-0">Mensaje de Texto (SMS)</p>
                <p class="text-[11px] text-slate-500 m-0">Respaldo telefónico sin necesidad de conexión de datos</p>
              </div>
            </div>
            <q-checkbox
              v-model="selectedChannels"
              val="SMS"
              color="info"
              dense
            />
          </div>

          <!-- Voice Call -->
          <div
            class="flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer"
            :class="selectedChannels.includes('VOICE_CALL') ? 'bg-amber-50/50 border-amber-300' : 'bg-slate-50 border-slate-200'"
            @click="toggleChannel('VOICE_CALL')"
          >
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 rounded-lg bg-amber-600 text-white flex items-center justify-center shadow-xs">
                <q-icon name="phone" size="18px" />
              </div>
              <div>
                <p class="text-xs font-bold text-slate-800 m-0">Llamada Automática de Voz (TTS)</p>
                <p class="text-[11px] text-slate-500 m-0">Aviso hablado para citas urgentes o emergencias</p>
              </div>
            </div>
            <q-checkbox
              v-model="selectedChannels"
              val="VOICE_CALL"
              color="warning"
              dense
            />
          </div>
        </div>

        <!-- Dispositivos FCM Registrados -->
        <div class="pt-2 border-t border-slate-100">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-slate-800">Dispositivos Vinculados (FCM)</span>
            <q-btn
              flat
              dense
              no-caps
              size="sm"
              color="primary"
              icon="add_to_home_screen"
              label="Vincular este navegador"
              :loading="registeringDevice"
              @click="registerCurrentDevice"
            />
          </div>
          <div v-if="devices.length === 0" class="text-[11px] text-slate-400 bg-slate-50 p-2.5 rounded-lg border border-dashed text-center">
            No tienes dispositivos vinculados. Haz clic en "Vincular este navegador" o abre la app móvil para recibir Push directos.
          </div>
          <div v-else class="space-y-1.5 max-h-32 overflow-y-auto">
            <div
              v-for="dev in devices"
              :key="dev.id"
              class="flex items-center justify-between text-xs bg-slate-50 p-2 rounded-lg border border-slate-200"
            >
              <div class="flex items-center space-x-2">
                <q-icon :name="dev.platform === 'android' ? 'android' : (dev.platform === 'ios' ? 'apple' : 'language')" size="16px" color="grey-7" />
                <span class="font-medium text-slate-700">{{ dev.device_name || 'Dispositivo' }}</span>
                <span class="text-[10px] text-slate-400">({{ dev.platform }})</span>
              </div>
              <q-btn
                flat
                round
                dense
                size="xs"
                icon="delete"
                color="negative"
                @click="unlinkDevice(dev.id)"
              />
            </div>
          </div>
        </div>

        <!-- Safe Fallback Note -->
        <div class="bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-start space-x-2.5">
          <q-icon name="security" size="18px" class="text-teal-700 shrink-0 mt-0.5" />
          <p class="text-[11px] text-slate-600 m-0 leading-relaxed">
            <span class="font-bold text-slate-800">Garantía de Entrega:</span> Si un canal prioritario (como Push FCM o WhatsApp) no confirma entrega a tiempo, el sistema activará automáticamente el canal telefónico o correo de respaldo para asegurar que no pierdas tu cita.
          </p>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
        <q-btn
          flat
          label="Cancelar"
          color="grey-7"
          no-caps
          v-close-popup
        />
        <q-btn
          unelevated
          label="Guardar Preferencias"
          color="primary"
          no-caps
          class="font-semibold px-4"
          :loading="saving"
          @click="savePreferences"
        />
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { api } from 'boot/axios'
import { useQuasar } from 'quasar'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const $q = useQuasar()
const isOpen = ref(props.modelValue)
const loading = ref(false)
const saving = ref(false)
const registeringDevice = ref(false)
const selectedChannels = ref(['PUSH', 'WHATSAPP', 'EMAIL'])
const devices = ref([])

watch(() => props.modelValue, (val) => {
  isOpen.value = val
  if (val) {
    loadPreferences()
    loadDevices()
  }
})

watch(isOpen, (val) => {
  emit('update:modelValue', val)
})

function toggleChannel(channel) {
  const idx = selectedChannels.value.indexOf(channel)
  if (idx >= 0) {
    if (selectedChannels.value.length > 1) {
      selectedChannels.value.splice(idx, 1)
    } else {
      $q.notify({
        type: 'warning',
        message: 'Debes mantener seleccionado al menos un canal.',
        position: 'top'
      })
    }
  } else {
    selectedChannels.value.push(channel)
  }
}

async function loadPreferences() {
  loading.value = true
  try {
    const res = await api.get('/api/v1/notifications/my-preferences')
    if (res.data?.preferred_notification_channels) {
      selectedChannels.value = res.data.preferred_notification_channels
    }
  } catch (err) {
    loggerError('Error cargando preferencias de notificación:', err)
  } finally {
    loading.value = false
  }
}

async function loadDevices() {
  try {
    const res = await api.get('/api/v1/notifications/devices')
    devices.value = res.data || []
  } catch (err) {
    loggerError('Error cargando dispositivos vinculados:', err)
  }
}

async function registerCurrentDevice() {
  registeringDevice.value = true
  try {
    // Generar o registrar token local de navegador
    const browserToken = `fcm_web_${navigator.userAgent.replace(/[^a-zA-Z0-9]/g, '').slice(0, 20)}_${Date.now()}`
    const deviceName = `${navigator.platform || 'Navegador Web'} (${navigator.userAgent.includes('Chrome') ? 'Chrome' : 'Navegador'})`
    
    await api.post('/api/v1/notifications/devices', {
      fcm_token: browserToken,
      platform: 'web',
      device_name: deviceName
    })

    $q.notify({
      type: 'positive',
      message: 'Navegador vinculado con éxito para notificaciones Push.',
      position: 'top'
    })
    await loadDevices()
    if (!selectedChannels.value.includes('PUSH')) {
      selectedChannels.value.push('PUSH')
    }
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al vincular el dispositivo.',
      position: 'top'
    })
  } finally {
    registeringDevice.value = false
  }
}

async function unlinkDevice(deviceId) {
  try {
    await api.delete(`/api/v1/notifications/devices/${deviceId}`)
    $q.notify({
      type: 'info',
      message: 'Dispositivo desvinculado.',
      position: 'top'
    })
    await loadDevices()
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: 'No se pudo desvincular el dispositivo.',
      position: 'top'
    })
  }
}

async function savePreferences() {
  if (!selectedChannels.value.length) {
    $q.notify({
      type: 'warning',
      message: 'Debes seleccionar al menos un canal de notificación.',
      position: 'top'
    })
    return
  }

  saving.value = true
  try {
    await api.put('/api/v1/notifications/my-preferences', {
      preferred_notification_channels: selectedChannels.value
    })
    $q.notify({
      type: 'positive',
      message: 'Preferencias de notificación guardadas correctamente.',
      position: 'top'
    })
    isOpen.value = false
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al guardar preferencias.',
      position: 'top'
    })
  } finally {
    saving.value = false
  }
}

function loggerError(...args) {
  console.error(...args)
}
</script>
