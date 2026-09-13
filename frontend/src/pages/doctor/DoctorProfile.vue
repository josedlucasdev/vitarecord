<template>
  <q-page class="p-4 sm:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-5xl mx-auto space-y-6">
      <!-- 1. Encabezado del Perfil -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-xl shadow-sm">
            <q-icon name="badge" size="28px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">Mi Perfil Profesional y Presencia Pública</h1>
            <p class="text-xs text-slate-500">
              Gestiona tus títulos universitarios, experiencia laboral y biografía visibles en el Directorio Médico VitaRecord.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <q-btn
            outline
            color="teal-8"
            icon="visibility"
            label="Ver en Directorio"
            to="/doctors"
            target="_blank"
            no-caps
            class="text-xs font-semibold"
          />
          <q-btn
            unelevated
            color="primary"
            icon="save"
            label="Guardar Cambios"
            :loading="saving"
            no-caps
            class="text-xs font-bold shadow-sm"
            @click="saveProfile"
          />
        </div>
      </div>

      <div v-if="loading" class="text-center py-12">
        <q-spinner-dots color="teal" size="48px" />
        <p class="text-xs text-slate-500 mt-2">Cargando perfil profesional...</p>
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Columna Izquierda: Formulario Principal (2 Cols) -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Datos Generales y Biografía -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-5">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <q-icon name="person" color="teal" size="18px" />
              Información Profesional & Visibilidad
            </h2>

            <!-- Foto de Perfil Profesional -->
            <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row items-center gap-5">
              <div class="relative group shrink-0">
                <div class="w-24 h-24 rounded-2xl bg-gradient-to-tr from-teal-700 to-teal-500 text-white flex items-center justify-center font-bold text-2xl shadow-md overflow-hidden border-2 border-white ring-2 ring-teal-100">
                  <img
                    v-if="profile.profile_picture_url"
                    :src="profile.profile_picture_url"
                    class="w-full h-full object-cover"
                    alt="Foto de perfil"
                  />
                  <span v-else>{{ getInitials(profile.full_name) }}</span>
                </div>
                <div v-if="uploadingAvatar" class="absolute inset-0 bg-black/40 rounded-2xl flex items-center justify-center">
                  <q-spinner color="white" size="24px" />
                </div>
              </div>

              <div class="flex-1 text-center sm:text-left space-y-1">
                <div class="text-sm font-bold text-slate-800">Fotografía Profesional de Perfil</div>
                <div class="text-xs text-slate-500 leading-relaxed">
                  Sube tu foto profesional oficial. Se mostrará a tus pacientes en el Directorio Médico y en tus recetas emitidas.
                </div>
                <div class="flex flex-wrap items-center justify-center sm:justify-start gap-2 pt-1.5">
                  <input
                    ref="avatarInputRef"
                    type="file"
                    accept="image/png, image/jpeg, image/webp"
                    class="hidden"
                    @change="handleAvatarFileSelect"
                  />
                  <q-btn
                    unelevated
                    dense
                    size="sm"
                    color="teal-8"
                    icon="photo_camera"
                    label="Subir Fotografía"
                    :loading="uploadingAvatar"
                    no-caps
                    class="px-3 py-1 font-semibold"
                    @click="triggerAvatarUpload"
                  />
                  <q-btn
                    v-if="profile.profile_picture_url"
                    outline
                    dense
                    size="sm"
                    color="negative"
                    icon="delete"
                    label="Eliminar"
                    :loading="deletingAvatar"
                    no-caps
                    class="px-2 py-1 text-xs"
                    @click="removeAvatar"
                  />
                </div>
                <div class="text-3xs text-slate-400">Formatos permitidos: JPG, PNG, WEBP. Máximo 5 MB.</div>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <q-input
                v-model="profile.full_name"
                label="Nombre Completo"
                outlined
                dense
                disable
                hint="Verificado con tu matrícula profesional"
              />
              <q-input
                v-model="profile.license_number"
                label="Matrícula / Registro Médico"
                outlined
                dense
                disable
                hint="Validado por Compliance VitaRecord"
              />
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <q-input
                v-model="profile.specialty"
                label="Especialidad Médica Principal"
                outlined
                dense
                placeholder="Ej. Ginecología & Obstetricia"
              />
              <q-input
                v-model="profile.phone"
                label="Teléfono de Contacto Profesional"
                outlined
                dense
                placeholder="+58 412 0000000"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Biografía / Resumen Profesional para Pacientes
              </label>
              <q-input
                v-model="profile.biography"
                type="textarea"
                rows="4"
                outlined
                dense
                counter
                maxlength="1000"
                placeholder="Describe tu enfoque clínico, trayectoria, áreas de interés y compromiso con la atención del paciente..."
              />
            </div>

            <div class="pt-2 border-t border-slate-100 flex items-center justify-between">
              <div>
                <div class="text-xs font-bold text-slate-800">Visibilidad en el Directorio Público</div>
                <div class="text-3xs text-slate-500">Permite que pacientes puedan encontrarte y agendar citas en línea</div>
              </div>
              <q-toggle v-model="profile.is_public_profile_enabled" color="teal" />
            </div>
          </div>

          <!-- Sedes Clínicas Afiliadas & Centros de Trabajo -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <q-icon name="apartment" color="teal" size="18px" />
                  Sedes Clínicas Afiliadas
                </h2>
                <p class="text-xs text-slate-500 mt-0.5">
                  Centros de salud donde estás habilitado para atender citas médicas y gestionar horarios.
                </p>
              </div>
              <span class="px-2.5 py-1 rounded-full text-2xs font-extrabold bg-teal-50 text-teal-700 border border-teal-100">
                {{ (profile.clinics && profile.clinics.length) || 0 }} {{ (profile.clinics && profile.clinics.length === 1) ? 'Sede Activa' : 'Sedes Activas' }}
              </span>
            </div>

            <div v-if="profile.clinics && profile.clinics.length > 0" class="space-y-3">
              <div
                v-for="clinic in profile.clinics"
                :key="clinic.id"
                class="p-4 rounded-xl border border-slate-200 bg-slate-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div class="flex items-start gap-3">
                  <div class="w-10 h-10 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center font-bold shrink-0 mt-0.5">
                    <q-icon name="local_hospital" size="20px" />
                  </div>
                  <div>
                    <div class="font-bold text-sm text-slate-900 flex items-center gap-2">
                      <span>{{ clinic.name }}</span>
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-emerald-100 text-emerald-800">
                        <q-icon name="check_circle" size="10px" color="positive" />
                        AFILIACIÓN ACTIVA
                      </span>
                    </div>
                    <div class="text-xs text-slate-500 flex flex-wrap items-center gap-x-3 gap-y-1 mt-0.5">
                      <span v-if="clinic.timezone" class="flex items-center gap-1">
                        <q-icon name="schedule" size="12px" color="slate-400" />
                        {{ clinic.timezone }}
                      </span>
                      <span v-if="clinic.country_code" class="flex items-center gap-1 font-mono text-3xs uppercase">
                        <q-icon name="flag" size="12px" color="slate-400" />
                        {{ clinic.country_code }}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="sm:self-center">
                  <q-btn
                    outline
                    dense
                    color="negative"
                    icon="link_off"
                    label="Desvincularme"
                    no-caps
                    class="text-xs font-semibold px-3 py-1 bg-white hover:bg-rose-50"
                    @click="confirmDisaffiliation(clinic)"
                  >
                    <q-tooltip>Dejar de atender en esta sede y notificar a la administración</q-tooltip>
                  </q-btn>
                </div>
              </div>
            </div>

            <div v-else class="text-xs text-slate-400 p-6 text-center border-2 border-dashed border-slate-200 rounded-xl space-y-1">
              <q-icon name="domain_disabled" size="32px" color="slate-300" class="mb-1" />
              <div class="font-semibold text-slate-600">No tienes sedes clínicas vinculadas actualmente.</div>
              <p class="text-3xs text-slate-400">
                Las clínicas pueden enviarte una invitación para autorizar consultorios y turnos en su centro.
              </p>
            </div>
          </div>

          <!-- Títulos Universitarios y Certificaciones -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <q-icon name="school" color="teal" size="18px" />
                Títulos Académicos & Certificaciones
              </h2>
              <q-btn
                unelevated
                size="sm"
                color="teal-8"
                icon="add"
                label="Agregar Título"
                no-caps
                @click="openAddDegreeModal"
              />
            </div>

            <div v-if="profile.academic_degrees && profile.academic_degrees.length > 0" class="space-y-3">
              <div
                v-for="(degree, idx) in profile.academic_degrees"
                :key="idx"
                class="p-4 rounded-xl border border-slate-200 bg-slate-50/60 flex items-start justify-between gap-3"
              >
                <div class="space-y-1">
                  <div class="font-bold text-sm text-slate-900">{{ degree.title }}</div>
                  <div class="text-xs text-teal-700 font-medium">{{ degree.institution }}</div>
                  <div class="text-3xs text-slate-500 flex items-center gap-3">
                    <span v-if="degree.year">Año: {{ degree.year }}</span>
                    <span v-if="degree.license_or_id">Registro: {{ degree.license_or_id }}</span>
                  </div>
                </div>
                <q-btn
                  flat
                  round
                  dense
                  color="negative"
                  icon="delete_outline"
                  size="sm"
                  @click="removeDegree(idx)"
                >
                  <q-tooltip>Eliminar titulación</q-tooltip>
                </q-btn>
              </div>
            </div>
            <div v-else class="text-xs text-slate-400 p-6 text-center border-2 border-dashed border-slate-200 rounded-xl">
              No has agregado títulos académicos. Haz clic en "Agregar Título" para registrar tus grados y diplomados.
            </div>
          </div>

          <!-- Experiencia Laboral e Institucional -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <q-icon name="work" color="teal" size="18px" />
                Trayectoria y Experiencia Laboral
              </h2>
              <q-btn
                unelevated
                size="sm"
                color="teal-8"
                icon="add"
                label="Agregar Experiencia"
                no-caps
                @click="openAddExperienceModal"
              />
            </div>

            <div v-if="profile.work_experience && profile.work_experience.length > 0" class="space-y-3">
              <div
                v-for="(exp, idx) in profile.work_experience"
                :key="idx"
                class="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2"
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <div class="font-bold text-sm text-slate-900">{{ exp.position }}</div>
                    <div class="text-xs text-slate-700 font-medium">{{ exp.workplace }}</div>
                    <div class="text-3xs text-slate-500 mt-0.5">
                      {{ exp.start_year || 'Inicio' }} — {{ exp.end_year ? exp.end_year : 'Actualidad' }}
                    </div>
                  </div>
                  <q-btn
                    flat
                    round
                    dense
                    color="negative"
                    icon="delete_outline"
                    size="sm"
                    @click="removeExperience(idx)"
                  >
                    <q-tooltip>Eliminar experiencia</q-tooltip>
                  </q-btn>
                </div>
                <p v-if="exp.description" class="text-xs text-slate-600 leading-relaxed pt-1 border-t border-slate-200/60">
                  {{ exp.description }}
                </p>
              </div>
            </div>
            <div v-else class="text-xs text-slate-400 p-6 text-center border-2 border-dashed border-slate-200 rounded-xl">
              No has documentado cargos o experiencia previa. Añade tu trayectoria para que los pacientes conozcan tu experiencia.
            </div>
          </div>

          <!-- Seguridad & Cambio de Contraseña -->
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <q-icon name="lock" color="teal" size="18px" />
                Seguridad y Contraseña de Acceso
              </h2>
              <span class="px-2 py-0.5 rounded text-3xs font-extrabold bg-blue-50 text-blue-700">
                Credenciales
              </span>
            </div>

            <p class="text-xs text-slate-500">
              Actualiza tu contraseña periódicamente para salvaguardar la privacidad de las historias clínicas y recetas emitidas.
            </p>

            <div class="space-y-3 max-w-md">
              <q-input
                v-model="passwordForm.currentPassword"
                :type="showCurrentPassword ? 'text' : 'password'"
                label="Contraseña Actual"
                outlined
                dense
                placeholder="Ingresa tu clave actual"
              >
                <template v-slot:append>
                  <q-icon
                    :name="showCurrentPassword ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="showCurrentPassword = !showCurrentPassword"
                  />
                </template>
              </q-input>

              <q-input
                v-model="passwordForm.newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                label="Nueva Contraseña"
                outlined
                dense
                placeholder="Mínimo 8 caracteres"
                hint="Debe tener al menos 8 caracteres"
              >
                <template v-slot:append>
                  <q-icon
                    :name="showNewPassword ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="showNewPassword = !showNewPassword"
                  />
                </template>
              </q-input>

              <q-input
                v-model="passwordForm.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                label="Confirmar Nueva Contraseña"
                outlined
                dense
                placeholder="Repite la nueva contraseña"
                :error="passwordMismatch"
                error-message="Las contraseñas no coinciden"
              >
                <template v-slot:append>
                  <q-icon
                    :name="showConfirmPassword ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="showConfirmPassword = !showConfirmPassword"
                  />
                </template>
              </q-input>

              <div class="pt-2">
                <q-btn
                  unelevated
                  color="teal-8"
                  icon="lock_reset"
                  label="Actualizar Contraseña"
                  :loading="changingPassword"
                  no-caps
                  class="font-bold text-xs shadow-sm"
                  @click="handleChangePassword"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Columna Derecha: Vista Previa en Vivo (1 Col) -->
        <div class="space-y-6">
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4 sticky top-6">
            <div class="flex items-center justify-between">
              <h2 class="text-xs font-bold uppercase tracking-wider text-slate-500">
                Vista Previa de tu Tarjeta
              </h2>
              <span class="px-2 py-0.5 rounded text-3xs font-extrabold bg-teal-50 text-teal-700">
                En vivo
              </span>
            </div>

            <!-- Mock Card del Directorio -->
            <div class="p-5 rounded-2xl border border-slate-200 bg-slate-50/40 space-y-4 shadow-sm">
              <div class="flex items-start gap-3">
                <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-teal-700 to-teal-500 text-white flex items-center justify-center font-bold text-lg shadow-sm shrink-0 overflow-hidden">
                  <img
                    v-if="profile.profile_picture_url"
                    :src="profile.profile_picture_url"
                    class="w-full h-full object-cover"
                    alt="Foto Dr."
                  />
                  <span v-else>{{ getInitials(profile.full_name) }}</span>
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-1 mb-0.5">
                    <span class="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded-full text-3xs font-extrabold bg-emerald-100 text-emerald-800">
                      <q-icon name="verified" size="10px" color="positive" />
                      VERIFICADO
                    </span>
                  </div>
                  <div class="text-sm font-bold text-slate-900 truncate">
                    {{ profile.full_name || 'Dr. Tu Nombre' }}
                  </div>
                  <div class="text-xs font-semibold text-teal-700">
                    {{ profile.specialty || 'Especialidad Médica' }}
                  </div>
                </div>
              </div>

              <p class="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                {{ profile.biography || 'Tu biografía y presentación médica aparecerán aquí ante los pacientes.' }}
              </p>

              <div v-if="profile.academic_degrees && profile.academic_degrees.length > 0" class="pt-1">
                <div class="inline-flex items-center gap-1.5 text-3xs text-slate-700 bg-teal-50 p-1.5 rounded-lg border border-teal-100 w-full truncate">
                  <q-icon name="school" size="14px" color="teal" />
                  <span class="truncate">{{ profile.academic_degrees[0].title }}</span>
                </div>
              </div>

              <div class="pt-2 border-t border-slate-200 flex gap-2">
                <q-btn outline dense color="slate-700" label="Ver Perfil" no-caps class="flex-1 text-2xs" />
                <q-btn unelevated dense color="teal-8" label="Agendar Cita" no-caps class="flex-1 text-2xs font-bold" />
              </div>
            </div>

            <div class="text-3xs text-slate-400 text-center leading-relaxed">
              Los cambios que guardes se reflejarán instantáneamente en el Directorio Médico VitaRecord.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Agregar Título -->
    <q-dialog v-model="showDegreeModal">
      <q-card class="w-full max-w-md rounded-2xl p-4">
        <q-card-section>
          <div class="text-base font-bold text-slate-900">Agregar Título Académico o Certificación</div>
          <div class="text-xs text-slate-500">Registra títulos de pregrado, posgrados o diplomados avalados.</div>
        </q-card-section>

        <q-card-section class="space-y-3">
          <q-input
            v-model="newDegree.title"
            label="Título o Grado Obtenido"
            outlined
            dense
            placeholder="Ej. Especialista en Ginecología"
          />
          <q-input
            v-model="newDegree.institution"
            label="Universidad o Institución Avalada"
            outlined
            dense
            placeholder="Ej. Universidad Central de Venezuela"
          />
          <div class="grid grid-cols-2 gap-2">
            <q-input
              v-model.number="newDegree.year"
              type="number"
              label="Año de Egreso"
              outlined
              dense
              placeholder="2018"
            />
            <q-input
              v-model="newDegree.license_or_id"
              label="N° Registro / Certificado"
              outlined
              dense
              placeholder="CMDF-1234"
            />
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancelar" color="slate-600" no-caps @click="showDegreeModal = false" />
          <q-btn unelevated color="teal-8" label="Agregar Titulación" no-caps class="font-bold" @click="addDegree" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Modal Agregar Experiencia -->
    <q-dialog v-model="showExperienceModal">
      <q-card class="w-full max-w-md rounded-2xl p-4">
        <q-card-section>
          <div class="text-base font-bold text-slate-900">Agregar Experiencia Laboral</div>
          <div class="text-xs text-slate-500">Documenta cargos hospitalarios, clínicas o jefaturas previas.</div>
        </q-card-section>

        <q-card-section class="space-y-3">
          <q-input
            v-model="newExp.position"
            label="Cargo o Rol Desempeñado"
            outlined
            dense
            placeholder="Ej. Cirujano Laparoscopista Adjunto"
          />
          <q-input
            v-model="newExp.workplace"
            label="Institución, Clínica u Hospital"
            outlined
            dense
            placeholder="Ej. Hospital Materno Infantil"
          />
          <div class="grid grid-cols-2 gap-2">
            <q-input
              v-model.number="newExp.start_year"
              type="number"
              label="Año de Inicio"
              outlined
              dense
              placeholder="2016"
            />
            <q-input
              v-model.number="newExp.end_year"
              type="number"
              label="Año de Fin (vacío = Actualidad)"
              outlined
              dense
              placeholder="2022"
            />
          </div>
          <q-input
            v-model="newExp.description"
            type="textarea"
            rows="2"
            label="Breve descripción de funciones o logros"
            outlined
            dense
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancelar" color="slate-600" no-caps @click="showExperienceModal = false" />
          <q-btn unelevated color="teal-8" label="Agregar Cargo" no-caps class="font-bold" @click="addExperience" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Modal Confirmar Desvinculación de Sede -->
    <q-dialog v-model="showDisaffiliateModal" persistent>
      <q-card class="w-full max-w-md rounded-2xl p-5">
        <q-card-section class="space-y-4">
          <div class="w-14 h-14 rounded-2xl bg-rose-50 border border-rose-100 text-rose-600 flex items-center justify-center font-bold mx-auto shadow-sm">
            <q-icon name="warning_amber" size="32px" />
          </div>

          <div class="text-center space-y-1">
            <h3 class="text-base font-bold text-slate-900">¿Confirmar Desvinculación de Sede?</h3>
            <p class="text-xs text-slate-500">
              Estás a punto de solicitar tu salida voluntaria de la sede médica:
            </p>
            <div class="font-bold text-sm text-teal-900 bg-teal-50 py-2.5 px-3 rounded-xl border border-teal-100 mt-2">
              {{ clinicToDisaffiliate?.name }}
            </div>
          </div>

          <div class="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1.5">
            <div class="font-bold flex items-center gap-1.5 text-amber-800">
              <q-icon name="info" size="16px" />
              Efectos inmediatos de esta acción:
            </div>
            <ul class="list-disc list-inside text-3xs space-y-1 text-amber-800 pl-1">
              <li>Tus turnos y horarios de atención en esta clínica serán desactivados.</li>
              <li>Dejarás de figurar en el directorio médico de esta sede ante los pacientes.</li>
              <li><strong>Se enviará una notificación por correo formal a la administración de la sede.</strong></li>
            </ul>
          </div>
        </q-card-section>

        <q-card-actions align="right" class="gap-2 pt-2">
          <q-btn
            flat
            label="Cancelar"
            color="slate-600"
            no-caps
            :disable="disaffiliating"
            @click="showDisaffiliateModal = false"
          />
          <q-btn
            unelevated
            color="negative"
            icon="link_off"
            label="Sí, Desvincularme"
            :loading="disaffiliating"
            no-caps
            class="font-bold text-xs shadow-sm"
            @click="executeDisaffiliation"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Notify } from 'quasar'
import { api } from 'boot/axios'

const loading = ref(true)
const saving = ref(false)

const profile = reactive({
  full_name: '',
  email: '',
  phone: '',
  specialty: '',
  biography: '',
  profile_picture_url: '',
  license_number: '',
  is_public_profile_enabled: true,
  academic_degrees: [],
  work_experience: [],
  clinics: []
})

// Gestión de Sedes y Desvinculación
const showDisaffiliateModal = ref(false)
const clinicToDisaffiliate = ref(null)
const disaffiliating = ref(false)

function confirmDisaffiliation (clinic) {
  clinicToDisaffiliate.value = clinic
  showDisaffiliateModal.value = true
}

async function executeDisaffiliation () {
  if (!clinicToDisaffiliate.value) return
  disaffiliating.value = true
  try {
    const clinicId = clinicToDisaffiliate.value.id
    const { data } = await api.post(`/doctors/me/clinics/${clinicId}/disaffiliate`)
    Notify.create({
      type: 'positive',
      message: data.message || 'Te has desvinculado exitosamente de la sede.',
      position: 'top',
      timeout: 5000
    })
    // Remover localmente la clínica
    profile.clinics = profile.clinics.filter(c => c.id !== clinicId)
    showDisaffiliateModal.value = false
    clinicToDisaffiliate.value = null
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al procesar la desvinculación de la sede.'
    })
  } finally {
    disaffiliating.value = false
  }
}

// Gestión de Fotografía de Perfil (Avatar)
const avatarInputRef = ref(null)
const uploadingAvatar = ref(false)
const deletingAvatar = ref(false)

function triggerAvatarUpload () {
  avatarInputRef.value?.click()
}

async function handleAvatarFileSelect (e) {
  const file = e.target.files?.[0]
  if (!file) return

  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    Notify.create({
      type: 'warning',
      message: 'Formato no soportado. Selecciona una imagen JPG, PNG o WEBP.'
    })
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    Notify.create({
      type: 'warning',
      message: 'La imagen supera los 5 MB de tamaño máximo permitido.'
    })
    return
  }

  uploadingAvatar.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post('/doctors/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    profile.profile_picture_url = `${data.profile_picture_url}?t=${Date.now()}`
    Notify.create({
      type: 'positive',
      message: '¡Foto de perfil actualizada exitosamente!'
    })
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al subir la fotografía de perfil.'
    })
  } finally {
    uploadingAvatar.value = false
    if (avatarInputRef.value) avatarInputRef.value.value = ''
  }
}

async function removeAvatar () {
  deletingAvatar.value = true
  try {
    await api.delete('/doctors/me/avatar')
    profile.profile_picture_url = ''
    Notify.create({
      type: 'positive',
      message: 'Foto de perfil eliminada. Se mostrarán tus iniciales.'
    })
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al eliminar la fotografía.'
    })
  } finally {
    deletingAvatar.value = false
  }
}

// Gestión de Cambio de Contraseña
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const changingPassword = ref(false)

const passwordMismatch = computed(() => {
  return passwordForm.confirmPassword.length > 0 && passwordForm.newPassword !== passwordForm.confirmPassword
})

async function handleChangePassword () {
  if (!passwordForm.currentPassword) {
    Notify.create({ type: 'warning', message: 'Por favor ingresa tu contraseña actual.' })
    return
  }
  if (!passwordForm.newPassword || passwordForm.newPassword.length < 8) {
    Notify.create({ type: 'warning', message: 'La nueva contraseña debe tener al menos 8 caracteres.' })
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    Notify.create({ type: 'warning', message: 'Las contraseñas no coinciden.' })
    return
  }

  changingPassword.value = true
  try {
    await api.post('/auth/change-password', {
      current_password: passwordForm.currentPassword,
      new_password: passwordForm.newPassword
    })
    Notify.create({
      type: 'positive',
      message: '¡Contraseña actualizada exitosamente!'
    })
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al actualizar la contraseña.'
    })
  } finally {
    changingPassword.value = false
  }
}

function getInitials (name) {
  if (!name) return 'DR'
  const parts = name.trim().split(' ').filter(Boolean)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

const showDegreeModal = ref(false)
const newDegree = reactive({
  title: '',
  institution: '',
  year: null,
  license_or_id: ''
})

const showExperienceModal = ref(false)
const newExp = reactive({
  position: '',
  workplace: '',
  start_year: null,
  end_year: null,
  description: ''
})

function openAddDegreeModal () {
  newDegree.title = ''
  newDegree.institution = ''
  newDegree.year = new Date().getFullYear()
  newDegree.license_or_id = ''
  showDegreeModal.value = true
}

function addDegree () {
  if (!newDegree.title || !newDegree.institution) {
    Notify.create({ type: 'warning', message: 'Indica al menos el título y la institución.' })
    return
  }
  profile.academic_degrees.push({ ...newDegree })
  showDegreeModal.value = false
}

function removeDegree (index) {
  profile.academic_degrees.splice(index, 1)
}

function openAddExperienceModal () {
  newExp.position = ''
  newExp.workplace = ''
  newExp.start_year = new Date().getFullYear() - 3
  newExp.end_year = null
  newExp.description = ''
  showExperienceModal.value = true
}

function addExperience () {
  if (!newExp.position || !newExp.workplace) {
    Notify.create({ type: 'warning', message: 'Indica el cargo y el lugar de trabajo.' })
    return
  }
  profile.work_experience.push({ ...newExp })
  showExperienceModal.value = false
}

function removeExperience (index) {
  profile.work_experience.splice(index, 1)
}

async function loadMyProfile () {
  loading.value = true
  try {
    const { data } = await api.get('/doctors/me/profile')
    profile.full_name = data.full_name || ''
    profile.email = data.email || ''
    profile.phone = data.phone || ''
    profile.specialty = data.specialty || ''
    profile.biography = data.biography || ''
    profile.profile_picture_url = data.profile_picture_url || ''
    profile.license_number = data.license_number || ''
    profile.is_public_profile_enabled = data.is_public_profile_enabled ?? true
    profile.academic_degrees = data.academic_degrees ? [...data.academic_degrees] : []
    profile.work_experience = data.work_experience ? [...data.work_experience] : []
    profile.clinics = data.clinics ? [...data.clinics] : []
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al cargar tu perfil profesional.' })
  } finally {
    loading.value = false
  }
}

async function saveProfile () {
  saving.value = true
  try {
    const payload = {
      biography: profile.biography,
      phone: profile.phone,
      specialty: profile.specialty,
      profile_picture_url: profile.profile_picture_url,
      is_public_profile_enabled: profile.is_public_profile_enabled,
      academic_degrees: profile.academic_degrees,
      work_experience: profile.work_experience
    }
    await api.put('/doctors/me/profile', payload)
    Notify.create({
      type: 'positive',
      message: '¡Perfil profesional actualizado exitosamente en VitaRecord!'
    })
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al guardar cambios de perfil.'
    })
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadMyProfile()
})
</script>
