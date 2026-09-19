<template>
  <q-layout view="lHh Lpr lFf" class="min-h-screen">
    <!-- Header simple sin drawer (oculto en pantallas de login por diseño inmersivo) -->
    <q-header v-if="!isLoginRoute" elevated style="background-color: #24796a !important;" class="text-white">
      <q-toolbar>
        <q-toolbar-title class="flex items-center cursor-pointer" @click="$router.push('/')">
          <img src="/icons/vitarecord-logo.png" alt="VitaRecord" class="w-8 h-8 rounded-full bg-white p-0.5 q-mr-sm" />
          <span class="font-bold tracking-tight">VitaRecord</span>
        </q-toolbar-title>

        <div class="row items-center q-gutter-sm">
          <q-btn
            flat
            dense
            icon="medical_services"
            label="Directorio Médico"
            to="/doctors"
            no-caps
            class="text-xs font-semibold"
          />

          <!-- Botón de Iniciar Sesión con Selector de Portal -->
          <q-btn-dropdown
            outline
            dense
            color="white"
            icon="login"
            label="Iniciar Sesión"
            no-caps
            class="text-xs font-bold"
          >
            <q-list class="text-slate-800 text-xs font-medium" style="min-width: 220px;">
              <q-item clickable v-close-popup to="/patient/login">
                <q-item-section avatar>
                  <q-icon name="favorite" color="teal" size="18px" />
                </q-item-section>
                <q-item-section>
                  <div class="font-bold">Portal Pacientes</div>
                  <div class="text-2xs text-slate-400">Citas y recetas médicas</div>
                </q-item-section>
              </q-item>

              <q-item clickable v-close-popup to="/clinic/login">
                <q-item-section avatar>
                  <q-icon name="medical_services" color="cyan-8" size="18px" />
                </q-item-section>
                <q-item-section>
                  <div class="font-bold">Personal Clínico</div>
                  <div class="text-2xs text-slate-400">Médicos, recepción y admin</div>
                </q-item-section>
              </q-item>

              <q-separator />

              <q-item clickable v-close-popup to="/admin/login">
                <q-item-section avatar>
                  <q-icon name="admin_panel_settings" color="indigo" size="18px" />
                </q-item-section>
                <q-item-section>
                  <div class="font-bold">Super Administrador</div>
                  <div class="text-2xs text-slate-400">Torre de control y SaaS</div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>
        </div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const isLoginRoute = computed(() => {
  return Boolean(
    route.meta?.hideHeader ||
    ['patient-login', 'clinic-login', 'admin-login', 'login'].includes(route.name)
  )
})
</script>
