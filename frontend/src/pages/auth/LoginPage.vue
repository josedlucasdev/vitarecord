<template>
  <div class="min-h-screen w-full relative flex items-center justify-center p-4 overflow-hidden bg-gradient-to-br from-slate-100 via-teal-50/40 to-sky-100/70">
    <!-- 1. Cuadrícula médica de fondo (estilo papel milimetrado clínico / telemetría modo claro) -->
    <div class="absolute inset-0 medical-grid opacity-85"></div>

    <!-- 2. Resplandores y halos de luz orgánica suave (Modo Claro) -->
    <div class="absolute w-[520px] h-[520px] rounded-full bg-teal-200/40 blur-[130px] pointer-events-none -top-24 -left-24 animate-pulse-slow"></div>
    <div class="absolute w-[620px] h-[620px] rounded-full bg-sky-200/50 blur-[150px] pointer-events-none -bottom-32 -right-32 animate-pulse-slow delay-1000"></div>
    <div class="absolute w-[380px] h-[380px] rounded-full bg-emerald-100/60 blur-[100px] pointer-events-none top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"></div>

    <!-- 3. Animación de Electrocardiograma (ECG / EKG Heartbeat en Modo Claro) -->
    <div class="absolute inset-0 pointer-events-none flex flex-col justify-around overflow-hidden opacity-45">
      <!-- Trazo ECG Superior -->
      <div class="ecg-track top-track">
        <svg class="ecg-svg" viewBox="0 0 1600 120" preserveAspectRatio="none">
          <path
            class="ecg-line ecg-line-teal"
            d="M 0,60 L 200,60 L 220,60 L 235,45 L 250,75 L 265,60 L 300,60 L 320,10 L 340,110 L 360,35 L 380,60 L 420,60 L 440,48 L 460,60 L 600,60 L 800,60 L 1000,60 L 1020,60 L 1035,45 L 1050,75 L 1065,60 L 1100,60 L 1120,10 L 1140,110 L 1160,35 L 1180,60 L 1220,60 L 1240,48 L 1260,60 L 1400,60 L 1600,60"
          />
        </svg>
      </div>

      <!-- Trazo ECG Central / Principal detrás de la tarjeta -->
      <div class="ecg-track center-track">
        <svg class="ecg-svg" viewBox="0 0 1600 120" preserveAspectRatio="none">
          <path
            class="ecg-line ecg-line-cyan"
            d="M 0,60 L 140,60 L 160,50 L 175,70 L 190,60 L 230,60 L 250,5 L 275,115 L 295,30 L 315,60 L 355,60 L 375,48 L 395,60 L 550,60 L 750,60 L 940,60 L 960,50 L 975,70 L 990,60 L 1030,60 L 1050,5 L 1075,115 L 1095,30 L 1115,60 L 1155,60 L 1175,48 L 1195,60 L 1350,60 L 1600,60"
          />
        </svg>
      </div>

      <!-- Trazo ECG Inferior -->
      <div class="ecg-track bottom-track">
        <svg class="ecg-svg" viewBox="0 0 1600 120" preserveAspectRatio="none">
          <path
            class="ecg-line ecg-line-blue"
            d="M 0,60 L 180,60 L 200,60 L 215,50 L 230,70 L 245,60 L 280,60 L 300,15 L 320,105 L 340,40 L 360,60 L 400,60 L 420,50 L 440,60 L 650,60 L 850,60 L 980,60 L 1000,60 L 1015,50 L 1030,70 L 1045,60 L 1080,60 L 1100,15 L 1120,105 L 1140,40 L 1160,60 L 1200,60 L 1220,50 L 1240,60 L 1450,60 L 1600,60"
          />
        </svg>
      </div>
    </div>

    <!-- 4. Elementos médicos flotantes (Cruces de salud, ADN, ritmo cardíaco en tono clínico claro) -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <!-- Cruz médica 1 -->
      <div class="med-float float-1">
        <svg class="w-8 h-8 text-teal-600/20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 10.5h-5.5V5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v5.5H5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5h5.5V19c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-5.5H19c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z"/>
        </svg>
      </div>
      <!-- Cruz médica 2 -->
      <div class="med-float float-2">
        <svg class="w-12 h-12 text-sky-600/18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 10.5h-5.5V5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v5.5H5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5h5.5V19c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-5.5H19c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z"/>
        </svg>
      </div>
      <!-- Cruz médica 3 -->
      <div class="med-float float-3">
        <svg class="w-6 h-6 text-emerald-600/22" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 10.5h-5.5V5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v5.5H5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5h5.5V19c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-5.5H19c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z"/>
        </svg>
      </div>
      <!-- Pulso cardíaco flotante -->
      <div class="med-float float-4">
        <svg class="w-10 h-10 text-teal-700/18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
        </svg>
      </div>
      <!-- Caduceo / Escudo flotante -->
      <div class="med-float float-5">
        <svg class="w-8 h-8 text-cyan-700/18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div>
    </div>

    <!-- 5. Tarjeta de Inicio de Sesión (Estilo Glassmorphism Clínico Profesional) -->
    <q-card
      class="relative z-10 w-full max-w-md bg-white/95 backdrop-blur-xl shadow-2xl rounded-3xl border border-slate-200/80 overflow-hidden"
      style="max-width: 420px;"
    >
      <!-- Cabecera Institucional VitaRecord -->
      <div class="bg-gradient-to-b from-slate-50 to-white pt-8 pb-4 px-6 text-center border-b border-slate-100">
        <div class="relative inline-flex items-center justify-center mb-3">
          <div class="absolute inset-0 rounded-2xl bg-teal-500/20 blur-md animate-pulse"></div>
          <img
            src="/icons/vitarecord-logo.png"
            alt="VitaRecord"
            class="relative w-20 h-20 rounded-2xl bg-white shadow-md p-1.5 border border-slate-100 object-contain"
          />
        </div>
        <h1 class="text-2xl font-black text-slate-900 tracking-tight flex items-center justify-center gap-1.5">
          <span>VitaRecord</span>
          <span class="w-2 h-2 rounded-full bg-teal-500"></span>
        </h1>
        <p class="text-xs font-semibold text-teal-700 mt-1 uppercase tracking-wider">
          Plataforma Clínica & Expediente Digital
        </p>
      </div>

      <!-- Formulario de Acceso -->
      <q-card-section class="px-6 py-6 space-y-4">
        <q-form class="space-y-4" @submit.prevent="onSubmit">
          <div>
            <label class="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              Correo Electrónico
            </label>
            <q-input
              v-model="email"
              type="email"
              placeholder="tu.correo@clinica.com"
              outlined
              dense
              class="rounded-xl"
              required
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
                to="/forgot-password"
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

          <div>
            <label class="block text-xs font-medium text-slate-500 mb-1">
              Código de Segundo Factor MFA (opcional)
            </label>
            <q-input
              v-model="mfaCode"
              placeholder="6 dígitos de tu app autenticadora"
              outlined
              dense
              class="rounded-xl"
            >
              <template v-slot:prepend>
                <q-icon name="security" size="18px" color="teal" />
              </template>
            </q-input>
          </div>

          <q-banner v-if="errorMessage" class="bg-red-50 text-red-800 rounded-xl text-xs border border-red-200">
            <template v-slot:avatar>
              <q-icon name="error_outline" color="red" />
            </template>
            {{ errorMessage }}
          </q-banner>

          <q-btn
            type="submit"
            color="teal-8"
            label="Iniciar Sesión"
            icon-right="arrow_forward"
            :loading="loading"
            class="full-width py-2.5 rounded-xl font-bold shadow-lg shadow-teal-700/20 text-white tracking-wide"
            no-caps
          />
        </q-form>

        <!-- Accesos directos para pruebas locales -->
        <div class="pt-4 border-t border-slate-100 text-caption">
          <div class="text-2xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            Perfiles de prueba rápida:
          </div>
          <div class="grid grid-cols-3 gap-1.5">
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200/60 hover:bg-indigo-100 transition-colors"
              @click="fillCreds('admin@intimasalud.com')"
            >
              SuperAdmin
            </button>
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-sky-50 text-sky-700 border border-sky-200/60 hover:bg-sky-100 transition-colors"
              @click="fillCreds('clinic.admin@intimasalud.com')"
            >
              Admin Clínica
            </button>
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-teal-50 text-teal-700 border border-teal-200/60 hover:bg-teal-100 transition-colors"
              @click="fillCreds('doctor@intimasalud.com')"
            >
              Médico
            </button>
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-amber-50 text-amber-800 border border-amber-200/60 hover:bg-amber-100 transition-colors"
              @click="fillCreds('recepcion@intimasalud.com')"
            >
              Recepción
            </button>
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200/60 hover:bg-emerald-100 transition-colors"
              @click="fillCreds('paciente@intimasalud.com')"
            >
              Paciente
            </button>
            <button
              type="button"
              class="px-2 py-1.5 text-2xs font-semibold rounded-lg bg-purple-50 text-purple-700 border border-purple-200/60 hover:bg-purple-100 transition-colors"
              @click="fillCreds('moderador@intimasalud.com')"
            >
              Compliance
            </button>
          </div>
          <div class="text-slate-400 text-center text-3xs mt-2">
            Clave universal: <span class="font-mono font-bold text-slate-600">Password123!</span>
          </div>
        </div>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { api } from 'boot/axios'
import { setAuthToken, useAcl } from 'src/composables/useAcl'

const email = ref('')
const password = ref('')
const mfaCode = ref('')
const loading = ref(false)
const errorMessage = ref('')

const router = useRouter()
const { isLoggedIn } = useAcl()

onMounted(() => {
  if (isLoggedIn.value) {
    router.replace({ name: 'home' })
  }
})

function fillCreds (userEmail) {
  email.value = userEmail
  password.value = 'Password123!'
  mfaCode.value = ''
  errorMessage.value = ''
}

async function onSubmit () {
  loading.value = true
  errorMessage.value = ''
  try {
    const form = new URLSearchParams()
    form.set('username', email.value)
    form.set('password', password.value)
    if (mfaCode.value) form.set('mfa_code', mfaCode.value)

    const { data } = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    setAuthToken(data.access_token, data.refresh_token)

    const redirectPath = router.currentRoute.value.query?.redirect
    if (redirectPath) {
      router.push(redirectPath)
    } else {
      router.push({ name: 'home' })
    }
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'No se pudo iniciar sesión'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Cuadrícula de telemetría médica (Modo Claro) */
.medical-grid {
  background-size: 40px 40px;
  background-image:
    linear-gradient(to right, rgba(15, 118, 110, 0.08) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(15, 118, 110, 0.08) 1px, transparent 1px);
}

/* Rieles de Electrocardiograma */
.ecg-track {
  width: 200%;
  height: 90px;
  display: flex;
}

.ecg-svg {
  width: 100%;
  height: 100%;
}

.ecg-line {
  fill: none;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.ecg-line-teal {
  stroke: #0d9488;
  filter: drop-shadow(0 0 6px rgba(13, 148, 136, 0.35));
}

.ecg-line-cyan {
  stroke: #0284c7;
  filter: drop-shadow(0 0 6px rgba(2, 132, 199, 0.35));
}

.ecg-line-blue {
  stroke: #2563eb;
  filter: drop-shadow(0 0 6px rgba(37, 99, 235, 0.3));
}

.top-track {
  animation: ecg-scroll 8s linear infinite;
}

.center-track {
  animation: ecg-scroll 5.5s linear infinite;
}

.bottom-track {
  animation: ecg-scroll 10s linear infinite;
}

@keyframes ecg-scroll {
  0% {
    transform: translate3d(0, 0, 0);
  }
  100% {
    transform: translate3d(-50%, 0, 0);
  }
}

/* Elementos médicos flotantes */
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

.float-4 {
  bottom: 18%;
  right: 10%;
  animation: float-slow 6.5s ease-in-out infinite 0.5s;
}

.float-5 {
  top: 70%;
  left: 30%;
  animation: float-slow 11s ease-in-out infinite 3s;
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
