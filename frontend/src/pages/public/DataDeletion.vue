<template>
  <div class="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-3xl mx-auto bg-white p-8 sm:p-12 rounded-3xl shadow-xl border border-slate-100 space-y-8">
      <!-- Header -->
      <div class="flex items-center space-x-4 border-b border-slate-100 pb-6">
        <img src="/icons/vitarecord-logo.png" alt="VitaRecord" class="w-14 h-14 rounded-2xl shadow-sm border border-slate-100 object-contain p-1" />
        <div>
          <h1 class="text-2xl font-black text-slate-900 m-0">Instrucciones de Eliminación de Datos</h1>
          <p class="text-xs font-semibold text-teal-700 m-0 uppercase tracking-wider">Cumplimiento Meta / Facebook & Plataforma VitaRecord</p>
        </div>
      </div>

      <!-- Introducción -->
      <div class="space-y-6 text-sm text-slate-700 leading-relaxed">
        <p>
          En <strong>VitaRecord</strong> respetamos plenamente su derecho al olvido y al control sobre su información. Conforme a las políticas de la plataforma Meta y las directrices de privacidad de datos, los usuarios que inicien sesión con Facebook o que mantengan una cuenta en VitaRecord pueden solicitar la eliminación total de sus datos personales y credenciales asociadas siguiendo cualquiera de los siguientes métodos:
        </p>

        <!-- Método 1: Desde la Configuración de Facebook -->
        <section class="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <div class="flex items-center space-x-2 font-bold text-slate-900 text-base">
            <q-icon name="smartphone" color="primary" size="20px" />
            <span>Método 1: Eliminar datos y revocar acceso desde Facebook</span>
          </div>
          <ol class="list-decimal list-inside space-y-2 text-slate-600 pl-2 text-xs leading-relaxed">
            <li>Inicie sesión en su cuenta de Facebook y vaya a <strong>Configuración y privacidad &gt; Configuración</strong>.</li>
            <li>En el menú lateral, busque y seleccione <strong>Apps y sitios web</strong>.</li>
            <li>Busque la aplicación <strong>Vita Record</strong> en la lista de aplicaciones conectadas.</li>
            <li>Haga clic en el botón <strong>Eliminar</strong> junto a la aplicación.</li>
            <li>Al confirmar, Facebook desvinculará su cuenta y notificará a nuestros servidores para purgar sus tokens de acceso y datos de sesión.</li>
          </ol>
        </section>

        <!-- Método 2: Solicitud Directa por Correo o Formulario -->
        <section class="p-5 rounded-2xl bg-teal-50/60 border border-teal-200 space-y-3">
          <div class="flex items-center space-x-2 font-bold text-teal-950 text-base">
            <q-icon name="mail" color="teal" size="20px" />
            <span>Método 2: Solicitud Directa a nuestro Oficial de Privacidad</span>
          </div>
          <p class="text-xs text-slate-600">
            También puede solicitar la eliminación completa de su expediente y datos de usuario enviando un correo electrónico desde la dirección registrada a:
          </p>
          <div class="bg-white p-3 rounded-xl border border-teal-100 font-mono text-xs text-teal-800 font-semibold">
            jsdlcs266@yahoo.com
          </div>
          <p class="text-xs text-slate-500 italic">
            Asunto: <code>Solicitud de Eliminación de Datos de Usuario - VitaRecord</code>. Su solicitud será procesada en un plazo máximo de 48 horas hábiles, confirmándole por escrito la purga de su cuenta de acuerdo con las normativas aplicables.
          </p>
        </section>
      </div>

      <!-- Footer Back Button -->
      <div class="pt-6 border-t border-slate-100 flex justify-between items-center text-xs">
        <router-link to="/privacy" class="text-teal-700 font-bold hover:underline flex items-center space-x-1">
          <q-icon name="arrow_back" size="14px" />
          <span>Ver Política de Privacidad</span>
        </router-link>
        <span class="text-slate-400">© 2026 VitaRecord</span>
      </div>
    </div>
  </div>
</template>

<script setup>
// Página estática de instrucciones de eliminación de datos (Data Deletion Instructions)
</script>
