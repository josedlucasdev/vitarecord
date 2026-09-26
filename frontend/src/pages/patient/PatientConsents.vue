<template>
  <q-page class="p-4 sm:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-4xl mx-auto space-y-6">
      <!-- Encabezado -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center space-x-3.5">
          <div class="w-12 h-12 rounded-xl bg-teal-600 text-white flex items-center justify-center shadow-sm">
            <q-icon name="verified_user" size="28px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900 leading-tight">Acceso a mi historia clínica</h1>
            <p class="text-xs text-slate-500 mt-0.5">
              Cada clínica ve solo lo que se registró en ella. Autoriza aquí a otra clínica para que sus médicos vean tu historial completo, por el tiempo que elijas.
            </p>
          </div>
        </div>
        <q-btn color="teal-8" icon="add" label="Autorizar clínica" no-caps unelevated @click="openGrantDialog" />
      </div>

      <!-- Lista de autorizaciones -->
      <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <q-inner-loading :showing="loading" />
        <div v-if="!loading && consents.length === 0" class="p-8 text-center text-slate-500 text-sm">
          Aún no has autorizado a ninguna clínica. Tu historial solo es visible en la clínica donde se generó.
        </div>
        <q-list v-else separator>
          <q-item v-for="c in consents" :key="c.id" class="py-4">
            <q-item-section avatar>
              <q-icon name="local_hospital" :color="c.status === 'ACTIVE' ? 'teal' : 'grey-5'" />
            </q-item-section>
            <q-item-section>
              <q-item-label class="font-semibold text-slate-800">{{ c.clinic_name || c.granted_to_clinic_id }}</q-item-label>
              <q-item-label caption>
                Otorgado el {{ formatDate(c.granted_at) }} ·
                <span v-if="c.status === 'ACTIVE'">vence el {{ formatDate(c.granted_until) }}</span>
                <span v-else-if="c.status === 'REVOKED'">revocado el {{ formatDate(c.revoked_at) }}</span>
                <span v-else>venció el {{ formatDate(c.granted_until) }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side class="flex flex-row items-center gap-2">
              <q-badge :color="statusColor(c.status)" :label="statusLabel(c.status)" />
              <q-btn
                v-if="c.status === 'ACTIVE'"
                flat
                dense
                no-caps
                color="negative"
                icon="block"
                label="Revocar"
                @click="revoke(c)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </div>
    </div>

    <!-- Diálogo para otorgar -->
    <q-dialog v-model="grantDialog.show">
      <q-card style="width: 460px; max-width: 95vw; border-radius: 16px;">
        <q-card-section class="bg-teal-700 text-white">
          <div class="text-h6">Autorizar a una clínica</div>
        </q-card-section>
        <q-card-section class="space-y-4">
          <q-select
            v-model="grantDialog.clinicId"
            :options="clinicOptions"
            option-value="id"
            option-label="name"
            emit-value
            map-options
            outlined
            dense
            label="Clínica"
          />
          <q-select
            v-model="grantDialog.days"
            :options="durationOptions"
            emit-value
            map-options
            outlined
            dense
            label="Duración"
          />
          <p class="text-xs text-slate-500">
            Los médicos que te atienden en esa clínica podrán consultar tu historia clínica de otras sedes. Puedes revocar el acceso en cualquier momento; cada consulta queda registrada.
          </p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" color="grey-7" v-close-popup />
          <q-btn unelevated color="teal-8" label="Autorizar" :disable="!grantDialog.clinicId" :loading="grantDialog.saving" @click="grant" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Dialog, Notify } from 'quasar'
import { api } from 'boot/axios'

const consents = ref([])
const loading = ref(false)
const clinicOptions = ref([])
const durationOptions = [
  { label: '7 días', value: 7 },
  { label: '30 días', value: 30 },
  { label: '90 días', value: 90 },
  { label: '1 año', value: 365 }
]
const grantDialog = reactive({ show: false, clinicId: null, days: 30, saving: false })

function formatDate (iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString([], { dateStyle: 'medium' })
}

function statusLabel (s) {
  return { ACTIVE: 'Vigente', REVOKED: 'Revocado', EXPIRED: 'Vencido' }[s] || s
}

function statusColor (s) {
  return { ACTIVE: 'positive', REVOKED: 'negative', EXPIRED: 'grey-6' }[s] || 'grey-6'
}

async function load () {
  loading.value = true
  try {
    const { data } = await api.get('/consents/my')
    consents.value = data
  } catch (err) {
    Notify.create({ type: 'negative', message: err.response?.data?.detail || 'No se pudieron cargar tus autorizaciones.' })
  } finally {
    loading.value = false
  }
}

async function openGrantDialog () {
  grantDialog.clinicId = null
  grantDialog.days = 30
  grantDialog.show = true
  if (!clinicOptions.value.length) {
    try {
      const { data } = await api.get('/clinics/public')
      clinicOptions.value = data
    } catch (err) {
      Notify.create({ type: 'negative', message: 'No se pudo cargar el listado de clínicas.' })
    }
  }
}

async function grant () {
  grantDialog.saving = true
  try {
    await api.post('/consents', { granted_to_clinic_id: grantDialog.clinicId, granted_days: grantDialog.days })
    grantDialog.show = false
    Notify.create({ type: 'positive', message: 'Autorización registrada.' })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.response?.data?.detail || 'No se pudo registrar la autorización.' })
  } finally {
    grantDialog.saving = false
  }
}

function revoke (consent) {
  Dialog.create({
    title: 'Revocar autorización',
    message: `Los médicos de ${consent.clinic_name || 'esta clínica'} dejarán de ver tu historial de otras sedes desde este momento.`,
    cancel: { label: 'Cancelar', flat: true },
    ok: { label: 'Revocar', color: 'negative', unelevated: true },
    persistent: true
  }).onOk(async () => {
    try {
      await api.post(`/consents/${consent.id}/revoke`)
      Notify.create({ type: 'positive', message: 'Autorización revocada.' })
      await load()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.response?.data?.detail || 'No se pudo revocar.' })
    }
  })
}

onMounted(load)
</script>
