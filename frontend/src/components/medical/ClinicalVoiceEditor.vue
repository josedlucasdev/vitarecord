<template>
  <div class="clinical-voice-editor space-y-1.5">
    <!-- Barra superior: Etiqueta y Controles (Micrófono + IA) -->
    <div class="flex items-center justify-between flex-wrap gap-2">
      <label class="block text-xs font-bold text-slate-700">
        {{ label }}
        <span v-if="required" class="text-red-500">*</span>
      </label>

      <div class="flex items-center space-x-2">
        <!-- Botón Dictado por Voz -->
        <q-btn
          :color="isRecording ? 'negative' : 'teal-8'"
          :flat="!isRecording"
          :unelevated="isRecording"
          size="sm"
          :icon="isRecording ? 'mic' : 'mic_none'"
          :label="isRecording ? 'Detener Micrófono' : 'Dictar'"
          :class="isRecording ? 'animate-pulse font-bold' : 'font-medium'"
          no-caps
          dense
          class="px-2 py-0.5 rounded-lg text-2xs"
          @click="toggleRecording"
        >
          <q-tooltip>
            {{ isRecording ? 'Detener dictado por voz' : 'Activar micrófono y dictar en español' }}
          </q-tooltip>
        </q-btn>

        <!-- Botón Mejorar con Inteligencia Artificial -->
        <q-btn
          v-if="aiEnabled"
          color="purple-8"
          outline
          size="sm"
          icon="auto_awesome"
          label="Mejorar con IA"
          no-caps
          dense
          :loading="aiLoading"
          class="px-2 py-0.5 rounded-lg text-2xs font-semibold bg-purple-50 hover:bg-purple-100 border-purple-300"
          @click="requestAiEnhancement"
        >
          <q-tooltip>
            Optimizar redacción clínica, ortografía y vocabulario médico con IA
          </q-tooltip>
        </q-btn>

        <q-badge
          v-else
          color="slate-3"
          text-color="slate-6"
          class="text-3xs py-1 px-2 cursor-not-allowed"
        >
          <q-icon name="auto_awesome" size="12px" class="mr-1 opacity-60" />
          IA no habilitada en sede
          <q-tooltip>
            El SuperAdmin puede habilitar el asistente de IA en la gestión de sedes clínicas.
          </q-tooltip>
        </q-badge>
      </div>
    </div>

    <!-- Indicador de Grabación Activa con feedback en vivo -->
    <div
      v-if="isRecording"
      class="p-2.5 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-red-900 animate-fadeIn"
    >
      <div class="flex items-center space-x-2 overflow-hidden mr-2">
        <span class="relative flex h-3 w-3 flex-shrink-0">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-3 w-3 bg-red-600"></span>
        </span>
        <span class="font-bold flex-shrink-0">Escuchando dictado:</span>
        <span class="truncate italic text-red-700">
          {{ interimTranscript || 'Hable con claridad hacia el micrófono...' }}
        </span>
      </div>
      <q-btn
        flat
        dense
        round
        size="xs"
        color="red-9"
        icon="stop_circle"
        @click="stopRecording"
      >
        <q-tooltip>Detener dictado</q-tooltip>
      </q-btn>
    </div>

    <!-- Editor Enriquecido Quasar con bordes nativos tipo outlined -->
    <div class="editor-container">
      <q-editor
        v-model="editorContent"
        :min-height="minHeight"
        :placeholder="placeholder"
        flat
        :toolbar="[
          ['bold', 'italic', 'underline'],
          ['unordered', 'ordered'],
          ['undo', 'redo', 'removeFormat']
        ]"
        :toolbar-color="'teal-8'"
        :toolbar-bg="'grey-1'"
        class="bg-white text-slate-800 text-xs"
        @update:model-value="onEditorChange"
      />
    </div>

    <!-- Modal de Revisión y Confirmación de Sugerencia de IA -->
    <q-dialog v-model="showAiReviewModal">
      <q-card style="min-width: 580px; max-width: 720px; border-radius: 16px;">
        <q-card-section class="bg-gradient-to-r from-purple-800 to-indigo-900 text-white p-4 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="auto_awesome" size="22px" />
            <div>
              <h3 class="text-base font-bold leading-tight">Asistente Clínico con Inteligencia Artificial</h3>
              <p class="text-2xs text-purple-200 mt-0.5 m-0">Propuesta de estructura y redacción médica profesional</p>
            </div>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-5 space-y-4">
          <p class="text-xs text-slate-600 leading-relaxed m-0">
            Revisa la propuesta médica generada por la IA antes de aplicarla. Puedes editar el texto directamente si deseas afinar algún término.
          </p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <!-- Columna Texto Original -->
            <div class="space-y-1">
              <span class="text-2xs font-bold text-slate-500 uppercase tracking-wide">Texto Original / Dictado:</span>
              <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 max-h-56 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {{ originalTextPreview }}
              </div>
            </div>

            <!-- Columna Texto IA -->
            <div class="space-y-1">
              <span class="text-2xs font-bold text-purple-800 uppercase tracking-wide flex items-center">
                <q-icon name="check_circle" size="14px" class="mr-1 text-purple-600" />
                Propuesta Mejorada:
              </span>
              <q-input
                v-model="aiEnhancedDraft"
                type="textarea"
                rows="7"
                outlined
                dense
                class="text-xs bg-purple-50/30 font-medium"
              />
            </div>
          </div>

          <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-2xs text-amber-900 flex items-start space-x-2">
            <q-icon name="verified_user" size="16px" class="text-amber-700 mt-0.5 flex-shrink-0" />
            <span>
              <strong>Validación médica obligatoria:</strong> La IA asiste en la redacción clínica formal, pero el médico tratante es el único responsable de la validez diagnóstica y terapéutica registrada en el expediente.
            </span>
          </div>
        </q-card-section>

        <q-card-actions align="right" class="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <q-btn flat label="Descartar" color="slate-7" v-close-popup no-caps />
          <div class="flex items-center space-x-2">
            <q-btn
              flat
              color="purple-9"
              label="Añadir al final"
              icon="post_add"
              no-caps
              class="text-xs font-semibold"
              @click="applyAiContent('append')"
            />
            <q-btn
              unelevated
              color="purple-8"
              label="Reemplazar campo"
              icon="check"
              no-caps
              class="text-xs font-semibold shadow-xs"
              @click="applyAiContent('replace')"
            />
          </div>
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    required: true
  },
  placeholder: {
    type: String,
    default: 'Escriba o active el micrófono para dictar...'
  },
  required: {
    type: Boolean,
    default: false
  },
  fieldType: {
    type: String,
    default: 'anamnesis' // anamnesis, physical_exam, diagnosis, plan
  },
  clinicId: {
    type: String,
    default: ''
  },
  aiEnabled: {
    type: Boolean,
    default: false
  },
  minHeight: {
    type: String,
    default: '6rem'
  }
})

const emit = defineEmits(['update:modelValue'])
const $q = useQuasar()

const editorContent = ref(props.modelValue || '')

watch(() => props.modelValue, (newVal) => {
  if (newVal !== editorContent.value) {
    editorContent.value = newVal || ''
  }
})

function onEditorChange (val) {
  emit('update:modelValue', val)
}

// ----------------------------------------------------
// Reconocimiento de Voz / Dictado (Web Speech API)
// ----------------------------------------------------
const isRecording = ref(false)
const interimTranscript = ref('')
let recognition = null

const SpeechRecognition = typeof window !== 'undefined'
  ? (window.SpeechRecognition || window.webkitSpeechRecognition || null)
  : null

function toggleRecording () {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

function startRecording () {
  if (!SpeechRecognition) {
    $q.notify({
      type: 'warning',
      message: 'Tu navegador no soporta reconocimiento de voz nativo (Web Speech API). Se recomienda Google Chrome, Microsoft Edge o Safari.',
      position: 'top'
    })
    return
  }

  try {
    recognition = new SpeechRecognition()
    recognition.lang = 'es-ES'
    recognition.continuous = true
    recognition.interimResults = true

    recognition.onstart = () => {
      isRecording.value = true
      interimTranscript.value = ''
    }

    recognition.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const item = event.results[i]
        if (item.isFinal) {
          const text = item[0]?.transcript?.trim()
          if (text) {
            appendDictationText(text)
          }
        } else {
          interim += item[0]?.transcript || ''
        }
      }
      interimTranscript.value = interim
    }

    recognition.onerror = (event) => {
      console.warn('SpeechRecognition error:', event.error)
      if (event.error === 'not-allowed') {
        $q.notify({
          type: 'negative',
          message: 'Permiso de micrófono denegado. Permite el acceso al micrófono en la barra del navegador.',
          position: 'top'
        })
      }
      stopRecording()
    }

    recognition.onend = () => {
      isRecording.value = false
      interimTranscript.value = ''
    }

    recognition.start()
  } catch (err) {
    console.error('Error al iniciar SpeechRecognition:', err)
    isRecording.value = false
  }
}

function stopRecording () {
  isRecording.value = false
  interimTranscript.value = ''
  if (recognition) {
    try {
      recognition.stop()
    } catch {}
    recognition = null
  }
}

function appendDictationText (text) {
  if (!text) return
  const formatted = text.charAt(0).toUpperCase() + text.slice(1)
  const current = (editorContent.value || '').trim()

  if (!current || current === '<p></p>' || current === '<p><br></p>') {
    editorContent.value = `<p>${formatted}.</p>`
  } else {
    editorContent.value = `${current}<p>${formatted}.</p>`
  }
  emit('update:modelValue', editorContent.value)
}

onBeforeUnmount(() => {
  stopRecording()
})

// ----------------------------------------------------
// Asistente Clínico de Inteligencia Artificial (IA)
// ----------------------------------------------------
const aiLoading = ref(false)
const showAiReviewModal = ref(false)
const originalTextPreview = ref('')
const aiEnhancedDraft = ref('')

function htmlToPlainText (htmlStr) {
  if (!htmlStr) return ''
  if (typeof document === 'undefined') return htmlStr
  const div = document.createElement('div')
  div.innerHTML = htmlStr
  return (div.innerText || div.textContent || '').trim()
}

function plainTextToHtml (text) {
  if (!text) return ''
  if (/<[a-z][\s\S]*>/i.test(text)) {
    return text
  }
  const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim().length > 0)
  if (paragraphs.length <= 1) {
    return `<p>${text.replace(/\n/g, '<br>')}</p>`
  }
  return paragraphs.map(p => `<p>${p.trim().replace(/\n/g, '<br>')}</p>`).join('')
}

async function requestAiEnhancement () {
  const plainText = htmlToPlainText(editorContent.value)
  if (!plainText || plainText.length < 5) {
    $q.notify({
      type: 'warning',
      message: 'Dicta o redacta información en este campo antes de solicitar la mejora con IA.',
      position: 'top'
    })
    return
  }

  aiLoading.value = true
  originalTextPreview.value = plainText

  try {
    const token = localStorage.getItem('access_token')
    const { data } = await api.post(
      '/medical-records/ai-assist',
      {
        clinic_id: props.clinicId,
        field_type: props.fieldType,
        text: plainText,
        tone: 'formal_clinical'
      },
      {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      }
    )

    aiEnhancedDraft.value = data.enhanced_text || plainText
    showAiReviewModal.value = true
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al conectar con el Asistente de IA.',
      position: 'top'
    })
  } finally {
    aiLoading.value = false
  }
}

function applyAiContent (mode) {
  const formattedHtml = plainTextToHtml(aiEnhancedDraft.value)
  if (mode === 'replace') {
    editorContent.value = formattedHtml
  } else if (mode === 'append') {
    const current = (editorContent.value || '').trim()
    if (!current || current === '<p></p>') {
      editorContent.value = formattedHtml
    } else {
      editorContent.value = `${current}${formattedHtml}`
    }
  }

  emit('update:modelValue', editorContent.value)
  showAiReviewModal.value = false

  $q.notify({
    type: 'positive',
    message: 'Texto clínico actualizado con la propuesta de IA.',
    position: 'top'
  })
}
</script>

<style scoped>
.clinical-voice-editor .editor-container {
  border: 1px solid rgba(0, 0, 0, 0.24);
  border-radius: 4px;
  background-color: #ffffff;
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
  overflow: hidden;
  box-sizing: border-box;
}

.clinical-voice-editor .editor-container:hover {
  border-color: rgba(0, 0, 0, 0.7);
}

.clinical-voice-editor .editor-container:focus-within {
  border-color: #24796a;
  box-shadow: 0 0 0 1px #24796a;
}

.clinical-voice-editor :deep(.q-editor) {
  border: none;
  border-radius: 4px;
}

.clinical-voice-editor :deep(.q-editor__toolbar) {
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
  background-color: #f8fafc;
  padding: 4px 8px;
  min-height: 36px;
}

.clinical-voice-editor :deep(.q-editor__content) {
  padding: 8px 12px;
  line-height: 1.5;
  font-size: 13px;
  color: #1e293b;
}
</style>
