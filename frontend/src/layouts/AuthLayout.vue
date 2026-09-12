<template>
  <q-layout view="lHh Lpr lFf" class="min-h-screen">
    <!-- Header simple sin drawer (oculto en login por requerimiento de diseño inmersivo) -->
    <q-header v-if="route.name !== 'login'" elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title class="flex items-center">
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
          <q-btn
            outline
            dense
            color="white"
            icon="login"
            label="Iniciar Sesión"
            to="/login"
            no-caps
            class="text-xs font-bold"
          />
        </div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>
