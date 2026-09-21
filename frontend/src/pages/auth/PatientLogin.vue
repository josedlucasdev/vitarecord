<template>
  <div class="min-h-screen w-full relative flex items-center justify-center p-4 overflow-hidden bg-gradient-to-br from-slate-100 via-teal-50/40 to-emerald-100/60">
    <!-- Cuadrícula médica de fondo -->
    <div class="absolute inset-0 medical-grid opacity-80"></div>

    <!-- Resplandores suaves -->
    <div class="absolute w-[500px] h-[500px] rounded-full bg-teal-200/40 blur-[130px] pointer-events-none -top-24 -left-24 animate-pulse-slow"></div>
    <div class="absolute w-[600px] h-[600px] rounded-full bg-emerald-200/40 blur-[150px] pointer-events-none -bottom-32 -right-32 animate-pulse-slow delay-1000"></div>

    <!-- Elementos médicos decorativos -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="med-float float-1">
        <svg class="w-8 h-8 text-teal-600/20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 10.5h-5.5V5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v5.5H5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5h5.5V19c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-5.5H19c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z"/>
        </svg>
      </div>
      <div class="med-float float-2">
        <svg class="w-10 h-10 text-emerald-600/18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
        </svg>
      </div>
      <div class="med-float float-3">
        <svg class="w-6 h-6 text-teal-700/20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 10.5h-5.5V5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v5.5H5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5h5.5V19c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-5.5H19c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z"/>
        </svg>
      </div>
    </div>

    <!-- Tarjeta de Login del Paciente -->
    <q-card
      class="relative z-10 w-full max-w-md bg-white/95 backdrop-blur-xl shadow-2xl rounded-3xl border border-slate-200/80 overflow-hidden"
      style="max-width: 430px;"
    >
      <!-- Cabecera Institucional VitaRecord Paciente -->
      <div class="bg-gradient-to-b from-teal-50/60 to-white pt-7 pb-4 px-6 flex flex-col items-center justify-center text-center border-b border-slate-100">
        <!-- 1. Logo arriba centrado -->
        <div class="relative flex items-center justify-center mb-3">
          <div class="absolute inset-0 rounded-2xl bg-teal-500/20 blur-md animate-pulse"></div>
          <img
            src="/icons/vitarecord-logo.png"
            alt="VitaRecord"
            class="relative w-16 h-16 rounded-2xl bg-white shadow-md p-1 border border-slate-100 object-contain mx-auto"
          />
        </div>

        <!-- 2. Luego debajo VitaRecord -->
        <h1 class="text-2xl font-black text-slate-900 tracking-tight mb-1.5">
          VitaRecord
        </h1>

        <!-- 3. Y luego Portal de Pacientes -->
        <div class="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-100/80 text-teal-800 text-xs font-bold uppercase tracking-wider mb-1">
          <q-icon name="favorite" size="13px" color="teal-8" />
          <span>Portal de Pacientes</span>
        </div>

        <p class="text-xs text-slate-500 mt-1">
          Accede a tus citas médicas, historial clínico y recetas digitales
        </p>
      </div>

      <!-- Formulario de Acceso -->
      <q-card-section class="px-6 py-5 space-y-4">
        <q-form class="space-y-4" @submit.prevent="onSubmit">
          <div>
            <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              Correo Electrónico
            </label>
            <q-input
              v-model="email"
              type="email"
              placeholder="tu.correo@ejemplo.com"
              outlined
              dense
              class="rounded-xl"
              required
              @blur="checkMfaStatus"
              @update:model-value="onEmailChange"
            >
              <template v-slot:prepend>
                <q-icon name="mail_outline" size="18px" color="teal" />
              </template>
            </q-input>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide">
                Contraseña
              </label>
              <router-link
                to="/patient/forgot-password"
                class="text-xs font-semibold text-teal-600 hover:text-teal-800 hover:underline"
              >
                ¿Olvidaste tu contraseña?
              </router-link>
            </div>
            <q-input
              v-model="password"
              type="password"
              placeholder="••••••••••••"
              outlined
              dense
              class="rounded-xl"
              required
            >
              <template v-slot:prepend>
                <q-icon name="lock_outline" size="18px" color="teal" />
              </template>
            </q-input>
          </div>

          <!-- Campo condicional de Segundo Factor MFA (Google Authenticator) -->
          <transition
            appear
            enter-active-class="animated fadeIn"
            leave-active-class="animated fadeOut"
          >
            <div v-if="showMfaField" class="space-y-1 p-3 rounded-xl bg-teal-50/50 border border-teal-200">
              <div class="flex items-center justify-between mb-1">
                <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide">
                  Código de Seguridad (Google Authenticator)
                </label>
                <span class="inline-flex items-center text-3xs font-bold text-teal-800 bg-teal-100 px-2 py-0.5 rounded-full">
                  <q-icon name="verified_user" size="11px" class="mr-1" />
                  MFA Activo
                </span>
              </div>
              <q-input
                ref="mfaInputRef"
                v-model="mfaCode"
                type="text"
                mask="######"
                placeholder="000000"
                outlined
                dense
                class="rounded-xl font-mono text-center tracking-widest text-base font-bold bg-white"
                required
              >
                <template v-slot:prepend>
                  <q-icon name="security" size="18px" color="teal-8" />
                </template>
              </q-input>
              <p class="text-3xs text-slate-500 m-0">
                Ingresa el código temporal de 6 dígitos de tu aplicación Google Authenticator.
              </p>
            </div>
          </transition>

          <q-banner v-if="errorMessage" class="bg-red-50 text-red-800 rounded-xl text-xs border border-red-200">
            <template v-slot:avatar>
              <q-icon name="error_outline" color="red" />
            </template>
            {{ errorMessage }}
          </q-banner>

          <q-btn
            type="submit"
            color="teal-8"
            label="Iniciar Sesión como Paciente"
            icon-right="arrow_forward"
            :loading="loading"
            class="full-width py-2.5 rounded-xl font-bold shadow-lg shadow-teal-700/20 text-white tracking-wide"
            no-caps
          />

          <!-- Divisor Social -->
          <div class="relative my-3.5">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-slate-200"></div>
            </div>
            <div class="relative flex justify-center text-xs">
              <span class="bg-white px-2 text-slate-400 font-medium">o ingresa con tus redes</span>
            </div>
          </div>

          <!-- Botón Google Login -->
          <div id="googleBtnContainer" class="w-full flex justify-center min-h-[40px] mb-2.5">
            <q-btn
              v-if="!googleButtonRendered"
              unelevated
              :loading="googleLoading"
              class="full-width py-2.5 rounded-xl font-bold bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 tracking-wide shadow-sm"
              no-caps
              @click="loginWithGoogle"
            >
              <template v-slot:default>
                <div class="flex items-center justify-center space-x-2.5">
                  <svg class="w-4 h-4" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"/>
                    <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"/>
                    <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.16 0 9.94 0 12s.45 3.84 1.25 5.42l4.03-3.15z"/>
                    <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/>
                  </svg>
                  <span>Continuar con Google</span>
                </div>
              </template>
            </q-btn>
          </div>

          <!-- Botón Facebook Login -->
          <q-btn
            unelevated
            :loading="fbLoading"
            class="full-width py-2.5 rounded-xl font-bold bg-[#1877F2] hover:bg-[#166fe5] text-white tracking-wide shadow-sm"
            no-caps
            @click="loginWithFacebook"
          >
            <template v-slot:default>
              <div class="flex items-center justify-center space-x-2.5">
                <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                <span>Continuar con Facebook</span>
              </div>
            </template>
          </q-btn>
        </q-form>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from 'boot/axios'
import { setAuthToken, clearAuthToken, useAcl, getValidTokenPayload } from 'src/composables/useAcl'

const email = ref('')
const password = ref('')
const mfaCode = ref('')
const showMfaField = ref(false)
const mfaInputRef = ref(null)
const loading = ref(false)
const fbLoading = ref(false)
const googleLoading = ref(false)
const googleButtonRendered = ref(false)
const errorMessage = ref('')

let emailDebounceTimer = null

function onEmailChange () {
  if (emailDebounceTimer) clearTimeout(emailDebounceTimer)
  emailDebounceTimer = setTimeout(() => {
    checkMfaStatus()
  }, 500)
}

async function checkMfaStatus () {
  const cleanEmail = (email.value || '').trim().toLowerCase()
  if (!cleanEmail || !cleanEmail.includes('@')) {
    showMfaField.value = false
    return
  }
  try {
    const { data } = await api.get(`/auth/mfa-status?email=${encodeURIComponent(cleanEmail)}`)
    showMfaField.value = !!data.mfa_enabled
    if (!data.mfa_enabled) {
      mfaCode.value = ''
    }
  } catch (err) {
    // Si falla la consulta no interrumpimos el flujo del usuario
  }
}

const router = useRouter()
const { isLoggedIn } = useAcl()

const GOOGLE_CLIENT_ID = '398180197268-bqtm2q48fp00vra1p5ar9uop02ed0p4u.apps.googleusercontent.com'

function initGoogleClient () {
  if (window.google?.accounts?.id) {
    try {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredentialResponse,
        auto_select: false
      })
      const container = document.getElementById('googleBtnContainer')
      if (container) {
        const targetWidth = Math.min(container.clientWidth || 370, 380)
        window.google.accounts.id.renderButton(container, {
          type: 'standard',
          shape: 'rectangular',
          theme: 'outline',
          text: 'continue_with',
          size: 'large',
          logo_alignment: 'center',
          width: targetWidth
        })
        googleButtonRendered.value = true
      }
    } catch (err) {
      console.warn('Error inicializando Google Identity Services:', err)
    }
  }
}

onMounted(() => {
  if (isLoggedIn.value) {
    router.replace({ name: 'home' })
  }

  // Inicializar Meta Facebook JavaScript SDK oficial
  if (!window.FB && !document.getElementById('facebook-jssdk')) {
    window.fbAsyncInit = function () {
      window.FB.init({
        appId: '1150121370684613',
        cookie: true,
        xfbml: true,
        version: 'v20.0'
      })
    }
    const script = document.createElement('script')
    script.id = 'facebook-jssdk'
    script.src = 'https://connect.facebook.net/es_LA/sdk.js'
    script.async = true
    script.defer = true
    document.head.appendChild(script)
  }

  // Inicializar Google Identity Services SDK
  if (!window.google && !document.getElementById('google-gsi-client')) {
    const gScript = document.createElement('script')
    gScript.id = 'google-gsi-client'
    gScript.src = 'https://accounts.google.com/gsi/client'
    gScript.async = true
    gScript.defer = true
    gScript.onload = () => {
      initGoogleClient()
    }
    document.head.appendChild(gScript)
  } else if (window.google) {
    initGoogleClient()
  }
})

function checkPatientRoleAndRedirect (accessToken, refreshToken) {
  if (!accessToken) {
    clearAuthToken()
    errorMessage.value = 'Respuesta no válida del servidor. No se recibió credencial de acceso.'
    return false
  }
  const payload = getValidTokenPayload(accessToken)
  if (!payload || payload.role !== 'PATIENT') {
    clearAuthToken()
    errorMessage.value = 'Acceso no autorizado: Este portal es exclusivo para pacientes. Si perteneces al personal clínico o administrativo, por favor ingresa por tu portal correspondiente.'
    return false
  }

  setAuthToken(accessToken, refreshToken)
  const redirectPath = router.currentRoute.value.query?.redirect
  if (redirectPath) {
    router.push(redirectPath)
  } else {
    router.push({ name: 'home' })
  }
  return true
}

async function loginWithGoogle () {
  googleLoading.value = true
  errorMessage.value = ''

  if (window.google?.accounts?.id) {
    window.google.accounts.id.prompt((notification) => {
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        googleLoading.value = false
      }
    })
  } else {
    await submitGoogleCredential('dev_google_paciente_demo')
  }
}

async function handleGoogleCredentialResponse (response) {
  if (response && response.credential) {
    await submitGoogleCredential(response.credential)
  }
}

async function submitGoogleCredential (credential) {
  googleLoading.value = true
  errorMessage.value = ''
  try {
    const { data } = await api.post('/auth/google', { credential })
    checkPatientRoleAndRedirect(data.access_token, data.refresh_token)
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Error al iniciar sesión con Google'
  } finally {
    googleLoading.value = false
  }
}

async function loginWithFacebook () {
  fbLoading.value = true
  errorMessage.value = ''

  if (window.FB) {
    window.FB.login((response) => {
      if (response.authResponse && response.authResponse.accessToken) {
        submitFacebookToken(response.authResponse.accessToken)
      } else {
        fbLoading.value = false
      }
    }, { scope: 'public_profile' })
  } else {
    await submitFacebookToken('dev_fb_paciente_demo')
  }
}

async function submitFacebookToken (token) {
  try {
    const { data } = await api.post('/auth/facebook', { access_token: token })
    checkPatientRoleAndRedirect(data.access_token, data.refresh_token)
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Error al iniciar sesión con Facebook'
  } finally {
    fbLoading.value = false
  }
}

async function onSubmit () {
  loading.value = true
  errorMessage.value = ''
  try {
    const form = new URLSearchParams()
    form.set('username', email.value)
    form.set('password', password.value)
    if (mfaCode.value) {
      form.set('mfa_code', mfaCode.value.trim().replace(/\D/g, ''))
    }

    const { data } = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    if (typeof data === 'string' && (data.includes('<!DOCTYPE') || data.includes('<html'))) {
      errorMessage.value = 'Error de conexión: El servidor devolvió una página HTML en lugar de la API. Verifica la URL del servicio.'
      return
    }

    if (!data || !data.access_token) {
      errorMessage.value = data?.detail || 'No se pudo iniciar sesión. Verifique sus credenciales.'
      return
    }

    checkPatientRoleAndRedirect(data.access_token, data.refresh_token)
  } catch (err) {
    const detail = err.response?.data?.detail || ''
    if (detail.includes('MFA') || err.response?.headers?.['x-mfa-required']) {
      showMfaField.value = true
      errorMessage.value = 'Tu cuenta tiene activada la verificación en dos pasos. Por favor ingresa el código de 6 dígitos de Google Authenticator.'
      setTimeout(() => mfaInputRef.value?.focus(), 150)
      return
    }
    errorMessage.value = detail || err.message || 'Credenciales inválidas o cuenta no activa'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.medical-grid {
  background-size: 40px 40px;
  background-image:
    linear-gradient(to right, rgba(13, 148, 136, 0.08) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(13, 148, 136, 0.08) 1px, transparent 1px);
}

.med-float {
  position: absolute;
}

.float-1 {
  top: 15%;
  left: 12%;
  animation: float-slow 7s ease-in-out infinite;
}

.float-2 {
  bottom: 20%;
  left: 8%;
  animation: float-slow 9s ease-in-out infinite 1s;
}

.float-3 {
  top: 25%;
  right: 14%;
  animation: float-slow 8s ease-in-out infinite 2s;
}

@keyframes float-slow {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-22px) rotate(4deg);
  }
}

.animate-pulse-slow {
  animation: pulse-slow 8s ease-in-out infinite alternate;
}

@keyframes pulse-slow {
  0% {
    opacity: 0.6;
    transform: scale(0.95);
  }
  100% {
    opacity: 1;
    transform: scale(1.05);
  }
}
</style>
