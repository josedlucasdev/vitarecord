<template>
  <q-dialog v-model="isOpen" persistent transition-show="scale" transition-hide="scale">
    <q-card style="width: 820px; max-width: 95vw; border-radius: 20px;" class="overflow-hidden shadow-2xl bg-slate-50 flex flex-col max-h-[92vh]">
      <!-- Header con gradiente clínico y badge de especialidad -->
      <div class="bg-gradient-to-r from-teal-800 via-teal-700 to-cyan-800 text-white p-5 flex items-center justify-between shadow-xs">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-2xl bg-white/15 backdrop-blur-xs flex items-center justify-center shadow-inner">
            <q-icon name="auto_awesome" size="26px" class="text-teal-200" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h2 class="text-base font-bold tracking-tight m-0">Consulta Médica Asistida por IA</h2>
              <q-badge color="teal-3" text-color="teal-10" class="font-bold text-3xs py-0.5 px-2 uppercase">
                Copiloto Clínico
              </q-badge>
            </div>
            <p class="text-xs text-teal-100 m-0 mt-0.5 flex items-center gap-1.5">
              <span>Especialidad activa:</span>
              <strong class="bg-white/20 px-2 py-0.5 rounded text-white">{{ doctorSpecialty || 'Medicina General' }}</strong>
            </p>
          </div>
        </div>
        <q-btn flat round dense icon="close" text-color="white" :disable="processingAi" @click="closeModal" />
      </div>

      <!-- Cuerpo del modal -->
      <q-card-section class="p-5 space-y-5 overflow-y-auto flex-1">
        <!-- Banner Explicativo -->
        <div class="p-3.5 bg-teal-50/80 border border-teal-200 rounded-xl flex items-start gap-3 text-xs text-teal-950">
          <q-icon name="info" size="20px" class="text-teal-700 shrink-0 mt-0.5" />
          <div>
            <span class="font-bold">¿Cómo funciona la consulta asistida?</span>
            <p class="m-0 mt-0.5 text-2xs text-teal-800 leading-relaxed">
              Active la grabación al iniciar la interacción con el paciente. El sistema grabará todo el diálogo mientras usted realiza el interrogatorio y exploración. Puede subir fotos de exámenes previos. Al detener la grabación, la IA analizará el caso desde la perspectiva de <strong>{{ doctorSpecialty || 'su especialidad' }}</strong> y prellenará automáticamente todos los campos de la consulta para su revisión.
            </p>
          </div>
        </div>

        <!-- 1. SECCIÓN DE GRABACIÓN DE AUDIO -->
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <q-icon name="mic" size="20px" :color="isRecording ? 'negative' : 'teal'" />
              <span class="text-xs font-bold uppercase tracking-wider text-slate-700">
                1. Grabación del Diálogo Médico-Paciente
              </span>
            </div>
            <div v-if="isRecording" class="flex items-center space-x-2 bg-red-50 text-red-700 px-3 py-1 rounded-full text-xs font-bold animate-pulse">
              <span class="w-2.5 h-2.5 rounded-full bg-red-600 inline-block"></span>
              <span>GRABANDO EN VIVO: {{ formattedTime }}</span>
            </div>
            <div v-else-if="audioBlob" class="bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full text-2xs font-bold flex items-center gap-1">
              <q-icon name="check_circle" size="14px" />
              <span>Audio Capturado ({{ formattedTime }})</span>
            </div>
          </div>

          <!-- Visualizador de Onda / Nivel de Audio cuando está grabando -->
          <div v-if="isRecording" class="p-4 bg-slate-900 rounded-xl text-center space-y-2">
            <div class="flex items-center justify-center gap-1.5 h-10">
              <span
                v-for="bar in audioBars"
                :key="bar.id"
                class="w-1.5 bg-teal-400 rounded-full transition-all duration-75"
                :style="{ height: `${bar.height}%` }"
              ></span>
            </div>
            <div class="text-3xs text-teal-300 font-mono">
              Micrófono activo • Capturando voz de médico y paciente en tiempo real
            </div>
          </div>

          <!-- Controles de Grabación -->
          <div class="flex flex-wrap items-center justify-center gap-3 pt-1">
            <q-btn
              v-if="!isRecording && !audioBlob"
              color="teal-8"
              icon="mic"
              label="Iniciar Grabación de Consulta"
              no-caps
              class="px-5 py-2.5 font-bold shadow-md rounded-xl text-xs"
              @click="startRecording"
            />

            <template v-else-if="isRecording">
              <q-btn
                color="negative"
                icon="stop"
                label="Detener Grabación"
                no-caps
                class="px-5 py-2.5 font-bold shadow-md rounded-xl text-xs"
                @click="stopRecording"
              />
              <q-btn
                flat
                dense
                color="slate-600"
                :icon="isPaused ? 'play_arrow' : 'pause'"
                :label="isPaused ? 'Reanudar' : 'Pausar'"
                no-caps
                class="text-xs px-3"
                @click="togglePauseRecording"
              />
            </template>

            <template v-else-if="audioBlob">
              <q-btn
                outline
                color="slate-700"
                icon="restart_alt"
                label="Grabar de Nuevo"
                no-caps
                dense
                class="text-xs px-3 py-1.5"
                @click="resetRecording"
              />
              <div class="flex-1 min-w-[240px]">
                <audio controls :src="audioPreviewUrl" class="w-full h-9 rounded-lg"></audio>
              </div>
            </template>
          </div>

          <!-- Previsualización de Transcripción en Vivo (desplegable) -->
          <div class="pt-2 border-t border-slate-100">
            <div class="flex items-center justify-between text-2xs text-slate-500 mb-1">
              <span class="font-semibold flex items-center gap-1">
                <q-icon name="subtitles" size="14px" />
                Transcripción del diálogo capturado:
              </span>
              <span v-if="transcript" class="text-3xs text-slate-400 font-mono">{{ transcript.length }} caracteres</span>
            </div>
            <q-input
              v-model="transcript"
              type="textarea"
              outlined
              dense
              rows="3"
              placeholder="El texto reconocido del diálogo aparecerá aquí en tiempo real mientras hablan. También puede editar o escribir detalles adicionales si lo desea."
              class="text-xs bg-slate-50/50"
            />
          </div>
        </div>

        <!-- 2. SECCIÓN DE DOCUMENTOS Y EXÁMENES APORTADOS -->
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div class="flex items-center space-x-2">
                <q-icon name="attach_file" size="20px" color="teal" />
                <span class="text-xs font-bold uppercase tracking-wider text-slate-700">
                  2. Documentos y Fotos de Exámenes / Otras Consultas
                </span>
              </div>
              <p class="text-2xs text-slate-500 m-0 mt-0.5">
                Suba fotos de ecografías, analíticas de sangre o informes previos que el paciente traiga a la consulta.
              </p>
            </div>

            <div>
              <input
                ref="fileInputRef"
                type="file"
                multiple
                accept="image/*,application/pdf"
                capture="environment"
                class="hidden"
                @change="handleFileUpload"
              />
              <q-btn
                outline
                color="teal-8"
                icon="add_a_photo"
                label="Tomar Foto / Subir Archivo"
                no-caps
                dense
                class="text-xs px-3 py-1.5 font-bold shadow-2xs"
                :loading="uploadingDoc"
                @click="triggerFileSelect"
              />
            </div>
          </div>

          <!-- Lista de Documentos Cargados para la Cita -->
          <div v-if="documentsList.length === 0" class="p-3 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center text-2xs text-slate-400">
            No se han adjuntado fotos ni documentos adicionales para esta consulta.
          </div>

          <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
            <div
              v-for="doc in documentsList"
              :key="doc.id"
              class="p-2.5 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between gap-2 text-xs"
            >
              <div class="flex items-center space-x-2 truncate">
                <div class="w-8 h-8 rounded-lg bg-teal-100 text-teal-800 flex items-center justify-center shrink-0">
                  <q-icon :name="doc.content_type?.startsWith('image/') ? 'image' : 'description'" size="16px" />
                </div>
                <div class="truncate">
                  <div class="font-bold text-slate-800 truncate text-2xs" :title="doc.file_name">
                    {{ doc.file_name }}
                  </div>
                  <div class="text-3xs text-slate-400">
                    {{ formatFileSize(doc.file_size) }}
                  </div>
                </div>
              </div>

              <div class="flex items-center">
                <q-btn
                  v-if="doc.download_url"
                  flat
                  round
                  dense
                  icon="visibility"
                  size="xs"
                  color="teal"
                  @click="openPreview(doc.download_url)"
                >
                  <q-tooltip>Ver anexo</q-tooltip>
                </q-btn>
                <q-btn
                  flat
                  round
                  dense
                  icon="delete"
                  size="xs"
                  color="negative"
                  @click="deleteDocument(doc.id)"
                >
                  <q-tooltip>Eliminar</q-tooltip>
                </q-btn>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. NOTAS ADICIONALES DEL MÉDICO -->
        <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <label class="block text-2xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1">
            <q-icon name="edit_note" size="16px" color="teal" />
            3. Notas u Observaciones Rápidas del Médico (Opcional)
          </label>
          <q-input
            v-model="doctorNotes"
            outlined
            dense
            placeholder="Ej: Sospecha de endometrioma, paciente refiere intolerancia a AINEs, antecedentes maternos de miomatosis..."
            class="text-xs"
          />
        </div>
      </q-card-section>

      <!-- Estado de Procesamiento Animado con IA -->
      <div v-if="processingAi" class="p-6 bg-teal-900/95 text-white flex flex-col items-center justify-center space-y-3">
        <q-spinner-orbit color="teal-2" size="48px" />
        <div class="text-sm font-bold text-center">
          Analizando consulta con IA especializada en {{ doctorSpecialty || 'Medicina General' }}...
        </div>
        <p class="text-2xs text-teal-200 max-w-md text-center m-0 leading-relaxed">
          Estructurando anamnesis, examen físico, diagnóstico diferencial con CIE-10 y plan terapéutico basado en el diálogo y los exámenes adjuntos.
        </p>
      </div>

      <!-- Footer de Acciones -->
      <q-card-actions align="between" class="bg-white p-4 px-6 border-t border-slate-200">
        <q-btn
          flat
          color="slate-600"
          label="Cancelar"
          no-caps
          :disable="processingAi"
          @click="closeModal"
        />

        <div class="flex items-center gap-2">
          <q-btn
            color="teal-8"
            icon="auto_awesome"
            label="Detener y Prellenar Consulta con IA"
            no-caps
            class="font-bold px-5 py-2 shadow-md rounded-xl text-xs"
            :loading="processingAi"
            :disable="!transcript.trim() && !audioBlob && !isRecording"
            @click="processAiAssistance"
          >
            <q-tooltip v-if="!transcript.trim() && !audioBlob && !isRecording">
              Inicie la grabación o ingrese notas del diálogo primero.
            </q-tooltip>
          </q-btn>
        </div>
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { api } from 'boot/axios'
import { Notify } from 'quasar'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  appointmentId: {
    type: String,
    required: true
  },
  doctorSpecialty: {
    type: String,
    default: 'Medicina General'
  },
  clinicId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'apply-prefill', 'audio-uploaded'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// Estados de Grabación de Audio
const isRecording = ref(false)
const isPaused = ref(false)
const recordingDurationSeconds = ref(0)
let timerInterval = null

let mediaRecorder = null
let audioChunks = []
let audioStream = null
const audioBlob = ref(null)
const audioPreviewUrl = ref('')

// Visualizador de onda de audio
let audioContext = null
let analyser = null
let animationFrameId = null
const audioBars = ref(
  Array.from({ length: 24 }, (_, i) => ({ id: i, height: 15 }))
)

// Transcripción en vivo
const transcript = ref('')
let recognition = null
let shouldKeepListening = false

// Documentos y fotos
const documentsList = ref([])
const uploadingDoc = ref(false)
const fileInputRef = ref(null)
const doctorNotes = ref('')
const processingAi = ref(false)

const formattedTime = computed(() => {
  const m = Math.floor(recordingDurationSeconds.value / 60)
  const s = recordingDurationSeconds.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

// Cargar documentos existentes de la cita al abrir
watch(isOpen, (newVal) => {
  if (newVal) {
    fetchAppointmentAttachments()
  } else {
    stopRecording(false)
  }
}, { immediate: true })


async function fetchAppointmentAttachments () {
  if (!props.appointmentId) return
  try {
    const { data } = await api.get(`/appointments/${props.appointmentId}/attachments`)
    documentsList.value = (data || []).filter(d => d.attachment_type !== 'CONSULTATION_AUDIO')
  } catch (err) {
    console.warn('No se pudieron cargar los anexos de la cita:', err)
  }
}

function triggerFileSelect () {
  if (fileInputRef.value) {
    fileInputRef.value.click()
  }
}

async function handleFileUpload (event) {
  const files = event.target?.files
  if (!files || files.length === 0) return

  uploadingDoc.value = true
  try {
    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('attachment_type', file.type.startsWith('image/') ? 'IMAGE' : 'LAB_RESULT')

      const { data } = await api.post(`/appointments/${props.appointmentId}/attachments`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      documentsList.value.push(data)
    }
    Notify.create({
      type: 'positive',
      message: `${files.length} documento(s) adjuntado(s) exitosamente a la consulta.`,
      icon: 'check_circle'
    })
  } catch (err) {
    console.error('Error al subir documento:', err)
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al subir documento.'
    })
  } finally {
    uploadingDoc.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

async function deleteDocument (docId) {
  try {
    await api.delete(`/appointments/${props.appointmentId}/attachments/${docId}`)
    documentsList.value = documentsList.value.filter(d => d.id !== docId)
    Notify.create({ type: 'info', message: 'Documento eliminado.' })
  } catch (err) {
    Notify.create({ type: 'negative', message: 'No se pudo eliminar el documento.' })
  }
}

function openPreview (url) {
  if (url) window.open(url, '_blank')
}

// -------------------------------------------------------------
// MOTOR DE AUDIO Y RECONOCIMIENTO DE VOZ CONTINUO
// -------------------------------------------------------------
async function startRecording () {
  try {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true })

    // Determinar formato soportado por el navegador
    let mimeType = 'audio/webm;codecs=opus'
    if (!MediaRecorder.isTypeSupported(mimeType)) {
      if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4'
      } else {
        mimeType = ''
      }
    }

    mediaRecorder = mimeType ? new MediaRecorder(audioStream, { mimeType }) : new MediaRecorder(audioStream)
    audioChunks = []

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        audioChunks.push(e.data)
      }
    }

    mediaRecorder.onstop = () => {
      const type = mediaRecorder?.mimeType || 'audio/webm'
      audioBlob.value = new Blob(audioChunks, { type })
      if (audioPreviewUrl.value) URL.revokeObjectURL(audioPreviewUrl.value)
      audioPreviewUrl.value = URL.createObjectURL(audioBlob.value)
    }

    mediaRecorder.start(1000)
    isRecording.value = true
    isPaused.value = false
    recordingDurationSeconds.value = 0

    timerInterval = setInterval(() => {
      if (!isPaused.value) {
        recordingDurationSeconds.value++
      }
    }, 1000)

    setupAudioVisualizer(audioStream)
    setupLiveTranscription()
  } catch (err) {
    console.error('Error al acceder al micrófono:', err)
    Notify.create({
      type: 'negative',
      message: 'No se pudo acceder al micrófono. Verifique los permisos del navegador.'
    })
  }
}

function setupAudioVisualizer (stream) {
  try {
    audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const source = audioContext.createMediaStreamSource(stream)
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 64
    source.connect(analyser)

    const dataArray = new Uint8Array(analyser.frequencyBinCount)

    const updateBars = () => {
      if (!isRecording.value) return
      analyser.getByteFrequencyData(dataArray)
      const count = audioBars.value.length
      const step = Math.floor(dataArray.length / count) || 1

      for (let i = 0; i < count; i++) {
        const val = dataArray[i * step] || 0
        const pct = Math.max(12, Math.min(95, (val / 255) * 100))
        audioBars.value[i].height = pct
      }
      animationFrameId = requestAnimationFrame(updateBars)
    }
    updateBars()
  } catch (e) {
    console.warn('Visualizador de audio no inicializado:', e)
  }
}

function setupLiveTranscription () {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    console.warn('SpeechRecognition no soportado en este navegador')
    return
  }

  shouldKeepListening = true
  try {
    recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'es-ES'

    recognition.onresult = (event) => {
      let finalTranscript = ''
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript + ' '
        }
      }
      if (finalTranscript) {
        transcript.value = (transcript.value + ' ' + finalTranscript).replace(/\s+/g, ' ').trim()
      }
    }

    recognition.onerror = (event) => {
      if (event.error === 'no-speech') {
        // Pausa normal en la conversación médico-paciente, no es error
        return
      }
      console.warn('Reconocimiento de voz:', event.error)
    }

    recognition.onend = () => {
      // Re-iniciar si el usuario sigue en sesión de grabación activa
      if (shouldKeepListening && isRecording.value) {
        try {
          recognition.start()
        } catch (_) {}
      }
    }

    recognition.start()
  } catch (e) {
    console.warn('No se pudo iniciar reconocimiento de voz continuo:', e)
  }
}

function stopRecording (save = true) {
  shouldKeepListening = false
  if (recognition) {
    try { recognition.stop() } catch (_) {}
  }
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
  if (audioContext && audioContext.state !== 'closed') {
    try { audioContext.close() } catch (_) {}
  }
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    try { mediaRecorder.stop() } catch (_) {}
  }
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop())
    audioStream = null
  }

  isRecording.value = false
  isPaused.value = false
}

function togglePauseRecording () {
  if (!mediaRecorder) return
  if (isPaused.value) {
    mediaRecorder.resume()
    isPaused.value = false
    shouldKeepListening = true
    try { recognition?.start() } catch (_) {}
  } else {
    mediaRecorder.pause()
    isPaused.value = true
    shouldKeepListening = false
    try { recognition?.stop() } catch (_) {}
  }
}

function resetRecording () {
  stopRecording(false)
  audioBlob.value = null
  if (audioPreviewUrl.value) {
    URL.revokeObjectURL(audioPreviewUrl.value)
    audioPreviewUrl.value = ''
  }
  transcript.value = ''
  recordingDurationSeconds.value = 0
}

// -------------------------------------------------------------
// PROCESAMIENTO Y PRELLENADO MEDIANTE IA
// -------------------------------------------------------------
async function processAiAssistance () {
  // Si todavía está grabando, detener primero
  if (isRecording.value) {
    stopRecording(true)
  }

  processingAi.value = true
  try {
    // 1. Si tenemos audio grabado, subirlo al servidor para que quede formalmente vinculado y reproducible
    if (audioBlob.value) {
      try {
        const formData = new FormData()
        const ext = audioBlob.value.type.includes('mp4') ? 'mp4' : 'webm'
        formData.append('file', audioBlob.value, `consulta_audio_${props.appointmentId.slice(0, 8)}.${ext}`)
        formData.append('attachment_type', 'CONSULTATION_AUDIO')

        const uploadRes = await api.post(`/appointments/${props.appointmentId}/attachments`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        emit('audio-uploaded', uploadRes.data)
      } catch (uploadErr) {
        console.warn('Aviso: No se pudo subir el audio al almacenamiento, se continúa con el análisis de texto:', uploadErr)
      }
    }

    // 2. Invocar el endpoint de asistencia clínica integral
    const payload = {
      appointment_id: props.appointmentId,
      transcript: transcript.value.trim() || 'Consulta médica sostenida con el paciente.',
      doctor_specialty: props.doctorSpecialty,
      extra_notes: doctorNotes.value.trim() || undefined
    }

    const { data } = await api.post('/medical-records/ai-consultation-assist', payload)

    emit('apply-prefill', {
      anamnesis: data.anamnesis,
      physical_exam: data.physical_exam,
      diagnosis: data.diagnosis,
      icd10_code: data.icd10_code,
      icd10_description: data.icd10_description,
      plan: data.plan,
      prescriptions: data.prescriptions || [],
      clinical_summary: data.clinical_summary
    })

    Notify.create({
      type: 'positive',
      message: '✨ Consulta estructurada exitosamente por IA. Campos prellenados listos para su revisión.',
      icon: 'verified',
      timeout: 4500
    })

    isOpen.value = false
  } catch (err) {
    console.error('Error al procesar consulta con IA:', err)
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudo completar el análisis con IA.'
    })
  } finally {
    processingAi.value = false
  }
}

function formatFileSize (bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function closeModal () {
  if (isRecording.value) {
    stopRecording(false)
  }
  isOpen.value = false
}

onBeforeUnmount(() => {
  stopRecording(false)
})
</script>
