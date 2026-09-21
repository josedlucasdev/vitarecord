<template>
  <q-page class="p-4 md:p-8 max-w-5xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-3xl shadow-xs border border-slate-200">
      <div>
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-teal-600 to-cyan-700 text-white flex items-center justify-center font-bold shadow-md shadow-teal-700/20">
            <q-icon name="event_available" size="26px" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900 leading-tight">Agendar Cita Médica</h1>
            <p class="text-xs text-slate-500">
              Reserva con garantía anti-solapamiento y registro de triage clínico para el especialista.
            </p>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <q-btn
          flat
          color="teal-8"
          icon="medical_services"
          label="Directorio Médico"
          to="/doctors"
          no-caps
          class="font-semibold text-xs"
        />
        <q-btn
          v-if="isLoggedIn"
          outline
          color="primary"
          icon="list_alt"
          label="Ver Mis Citas"
          to="/appointments/my-list"
          no-caps
          class="font-semibold text-xs"
        />
      </div>
    </div>

    <!-- Booking Form Card -->
    <div class="bg-white p-6 md:p-8 rounded-3xl shadow-xs border border-slate-200 space-y-8">
      <!-- SECCIÓN 1: ¿Para quién es la cita? (Modo Autenticado) o Identificación (Modo Público) -->
      <div v-if="isLoggedIn">
        <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
          1. Beneficiario de la Consulta
        </label>
        <div class="flex flex-wrap gap-3 items-center">
          <q-btn
            :outline="beneficiaryType !== 'self'"
            :color="beneficiaryType === 'self' ? 'primary' : 'grey-7'"
            icon="person"
            label="Para mí (Titular)"
            no-caps
            class="font-semibold"
            @click="selectSelf"
          />
          <q-btn
            :outline="beneficiaryType !== 'dependent'"
            :color="beneficiaryType === 'dependent' ? 'primary' : 'grey-7'"
            icon="family_restroom"
            label="Para un Familiar Dependiente"
            no-caps
            class="font-semibold"
            @click="selectDependentMode"
          />
          <q-btn
            v-if="beneficiaryType === 'dependent'"
            flat
            dense
            color="primary"
            icon="family_restroom"
            label="Gestionar Familiares"
            to="/patient/family"
            no-caps
            class="text-xs font-semibold"
          />
          <q-btn
            v-if="beneficiaryType === 'dependent'"
            flat
            dense
            color="teal-8"
            icon="add"
            label="Registro Rápido"
            no-caps
            class="text-xs font-semibold"
            @click="openQuickAddDependentModal"
          />
        </div>

        <div v-if="beneficiaryType === 'dependent'" class="mt-4 max-w-md">
          <q-select
            v-model="selectedDependentId"
            :options="dependentOptions"
            emit-value
            map-options
            outlined
            dense
            label="Selecciona al Familiar"
            :loading="loadingDependents"
          />
        </div>
      </div>

      <!-- SECCIÓN 1 (Pública): Datos Personales del Paciente y Dirección -->
      <div v-else class="space-y-4">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center">
            <q-icon name="person" size="16px" class="mr-1.5 text-teal-600" />
            1. Datos del Paciente y Contacto
          </label>
          <span class="text-2xs text-teal-700 bg-teal-50 px-2.5 py-1 rounded-full font-semibold border border-teal-200">
            No requieres cuenta previa para agendar
          </span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <q-input
            v-model="patientForm.full_name"
            outlined
            dense
            label="Nombre y Apellido *"
            placeholder="Ej. Ana Pérez"
            :rules="[val => !!val || 'El nombre es obligatorio']"
          />

          <q-input
            v-model="patientForm.id_document"
            outlined
            dense
            label="Cédula / Documento de Identidad *"
            placeholder="Ej. V-18765432"
            :rules="[val => !!val || 'El documento es obligatorio']"
          />

          <q-input
            v-model="patientForm.email"
            outlined
            dense
            type="email"
            label="Correo Electrónico *"
            placeholder="correo@ejemplo.com"
            hint="Aquí recibirás la confirmación e invitación con acceso"
            :rules="[val => !!val && /.+@.+\..+/.test(val) || 'Correo electrónico inválido']"
          />

          <q-input
            v-model="patientForm.phone"
            outlined
            dense
            label="Teléfono de Contacto *"
            placeholder="Ej. +58 412 1234567"
            :rules="[val => !!val || 'El teléfono es obligatorio']"
          />

          <q-input
            v-model="patientForm.birth_date"
            outlined
            dense
            type="date"
            label="Fecha de Nacimiento"
          />

          <q-select
            v-model="patientForm.gender"
            outlined
            dense
            :options="['Femenino', 'Masculino', 'Otro']"
            label="Sexo Biológico"
          />
        </div>

        <!-- Dirección de Residencia Simplificada -->
        <div class="pt-2">
          <div class="text-xs font-bold text-slate-600 mb-2 flex items-center">
            <q-icon name="home" size="15px" class="mr-1.5 text-teal-600" />
            Dirección de Residencia
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <q-input
              v-model="patientForm.country"
              outlined
              dense
              label="País"
              placeholder="Venezuela"
            />
            <q-input
              v-model="patientForm.city"
              outlined
              dense
              label="Ciudad / Estado"
              placeholder="Ej. Caracas, Miranda"
            />
            <q-input
              v-model="patientForm.address"
              outlined
              dense
              label="Dirección de Habitación"
              placeholder="Calle, Edificio / Casa, Nivel"
            />
          </div>
        </div>
      </div>

      <q-separator />

      <!-- SECCIÓN 2: Triage Clínico y Medidas Biométricas -->
      <!-- SECCIÓN 2: Triage Clínico y Medidas Biométricas -->
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-100 pb-2">
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center">
            <q-icon name="monitor_heart" size="16px" class="mr-1.5 text-teal-600" />
            2. Medidas Biométricas y Triage Clínico
          </label>
          <span class="text-2xs text-slate-500">
            Información médica para preparar tu consulta
          </span>
        </div>

        <!-- Caso A: El paciente titular o su familiar ya tiene su Ficha Clínica Basal (no se le vuelve a pedir) -->
        <div v-if="hasPermanentClinicalData" class="space-y-4">
          <!-- Tarjeta de Ficha Basal Registrada -->
          <div class="p-4 bg-teal-50/80 border border-teal-200 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
            <div class="space-y-1.5">
              <div class="flex items-center gap-2">
                <span class="text-2xs font-bold uppercase tracking-wider text-teal-800 flex items-center">
                  <q-icon name="verified" size="15px" class="mr-1 text-teal-600" />
                  {{ beneficiaryType === 'dependent' ? `Ficha Clínica Basal: ${selectedDependent?.full_name || 'Familiar'}` : 'Ficha Clínica Basal Permanente' }}
                </span>
                <span class="text-3xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold border border-emerald-300">
                  {{ beneficiaryType === 'dependent' ? 'Guardada en Núcleo Familiar' : 'Guardada en tu perfil' }}
                </span>
              </div>
              <div class="flex flex-wrap items-center gap-2 text-xs text-slate-700 pt-0.5">
                <span class="bg-white px-2.5 py-1 rounded-lg border border-teal-200 font-semibold flex items-center shadow-2xs">
                  <q-icon name="bloodtype" size="14px" class="mr-1 text-red-600" />
                  Grupo: <strong class="ml-1 text-teal-900">{{ patientForm.blood_type }}</strong>
                </span>
                <span class="bg-white px-2.5 py-1 rounded-lg border border-teal-200 font-semibold flex items-center shadow-2xs">
                  <q-icon name="straighten" size="14px" class="mr-1 text-teal-700" />
                  Talla: <strong class="ml-1 text-teal-900">{{ patientForm.height_cm }} cm</strong>
                </span>
                <span v-if="patientForm.allergies" class="bg-white px-2.5 py-1 rounded-lg border border-teal-200 text-slate-600 shadow-2xs flex items-center">
                  <q-icon name="warning" size="14px" class="mr-1 text-amber-600" />
                  Alergias: <strong class="ml-1 text-slate-800">{{ patientForm.allergies }}</strong>
                </span>
                <span v-if="patientForm.chronic_conditions" class="bg-white px-2.5 py-1 rounded-lg border border-teal-200 text-slate-600 shadow-2xs flex items-center">
                  <q-icon name="assignment" size="14px" class="mr-1 text-blue-600" />
                  Antecedentes: <strong class="ml-1 text-slate-800">{{ patientForm.chronic_conditions }}</strong>
                </span>
              </div>
            </div>

            <q-btn
              flat
              dense
              no-caps
              size="sm"
              color="teal-8"
              icon="edit"
              :label="beneficiaryType === 'dependent' ? 'Modificar en Familiares' : 'Modificar en Mi Perfil'"
              :to="beneficiaryType === 'dependent' ? '/patient/family' : '/patient/profile'"
              class="text-xs font-bold shrink-0 self-start sm:self-center"
            />
          </div>

          <!-- Campos requeridos de la consulta actual: Solo peso e indicaciones -->
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 bg-slate-50/80 p-4 rounded-2xl border border-slate-200">
            <div>
              <q-input
                v-model.number="patientForm.weight_kg"
                outlined
                dense
                type="number"
                step="0.1"
                label="Peso Actual de Consulta (kg) *"
                placeholder="Ej. 62.5"
                suffix="kg"
                bg-color="white"
                hint="El peso se registra en cada consulta"
                :rules="[val => !val || (val >= 2 && val <= 350) || 'Peso debe ser entre 2 y 350 kg']"
              />
            </div>

            <!-- Live BMI display usando la estatura fija del perfil -->
            <div class="flex items-center justify-center bg-white rounded-xl border border-slate-200 p-2.5">
              <div v-if="calculatedBmi" class="text-center">
                <div class="text-2xs font-bold uppercase tracking-wider text-slate-400">IMC (con tu talla {{ patientForm.height_cm }} cm)</div>
                <div class="text-lg font-black text-slate-800">{{ calculatedBmi }} <span class="text-xs font-normal text-slate-400">kg/m²</span></div>
                <span
                  :class="bmiCategoryClass"
                  class="inline-block px-2 py-0.5 rounded-full text-2xs font-bold mt-0.5"
                >
                  {{ bmiCategoryText }}
                </span>
              </div>
              <div v-else class="text-center text-slate-400 text-xs py-1">
                <q-icon name="calculate" size="18px" class="mb-1" />
                <div>Ingresa tu peso para calcular IMC</div>
              </div>
            </div>

            <div>
              <q-input
                v-model="patientForm.current_medications"
                outlined
                dense
                label="Medicamentos Actuales"
                placeholder="Ej. Losartán, Ninguno"
                bg-color="white"
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="teal"
                    label="No toma"
                    class="text-2xs font-bold"
                    @click="patientForm.current_medications = 'No consume medicamentos actualmente'"
                  />
                </template>
              </q-input>
            </div>
          </div>
        </div>

        <!-- Caso B: Paciente que aún no ha completado su ficha o reserva pública -->
        <div v-else class="space-y-4">
          <div v-if="isLoggedIn && beneficiaryType === 'self'" class="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-xs text-amber-900 leading-relaxed">
            <q-icon name="lightbulb" color="amber-8" size="18px" class="mt-0.5 shrink-0" />
            <div>
              <strong>Completa tus datos basales por primera vez:</strong>
              Ingresa tu estatura y grupo sanguíneo. Se guardarán en tu perfil de paciente para que no tengas que volver a ingresarlos en tus próximas consultas.
            </div>
          </div>
          <div v-else-if="isLoggedIn && beneficiaryType === 'dependent'" class="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-xs text-amber-900 leading-relaxed">
            <q-icon name="lightbulb" color="amber-8" size="18px" class="mt-0.5 shrink-0" />
            <div>
              <strong>Ficha médica incompleta para {{ selectedDependent?.full_name || 'este familiar' }}:</strong>
              Aún no tiene registrados su grupo sanguíneo y estatura fija. Puedes ingresarlos aquí para la consulta o guardarlos permanentemente en <router-link to="/patient/family" class="font-bold underline text-amber-950">Mis Familiares</router-link>.
            </div>
          </div>

          <!-- Medidas: Estatura, Peso e IMC -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-50/80 p-4 rounded-2xl border border-slate-200">
            <div>
              <q-input
                v-model.number="patientForm.height_cm"
                outlined
                dense
                type="number"
                label="Estatura / Talla (cm) *"
                placeholder="Ej. 165"
                suffix="cm"
                bg-color="white"
                :rules="[val => !val || (val >= 40 && val <= 250) || 'Talla debe ser entre 40 y 250 cm']"
              />
            </div>

            <div>
              <q-input
                v-model.number="patientForm.weight_kg"
                outlined
                dense
                type="number"
                step="0.1"
                label="Peso Actual (kg) *"
                placeholder="Ej. 62.5"
                suffix="kg"
                bg-color="white"
                :rules="[val => !val || (val >= 2 && val <= 350) || 'Peso debe ser entre 2 y 350 kg']"
              />
            </div>

            <!-- Live BMI display -->
            <div class="flex items-center justify-center bg-white rounded-xl border border-slate-200 p-2.5">
              <div v-if="calculatedBmi" class="text-center">
                <div class="text-2xs font-bold uppercase tracking-wider text-slate-400">IMC Calculado</div>
                <div class="text-lg font-black text-slate-800">{{ calculatedBmi }} <span class="text-xs font-normal text-slate-400">kg/m²</span></div>
                <span
                  :class="bmiCategoryClass"
                  class="inline-block px-2 py-0.5 rounded-full text-2xs font-bold mt-0.5"
                >
                  {{ bmiCategoryText }}
                </span>
              </div>
              <div v-else class="text-center text-slate-400 text-xs py-1">
                <q-icon name="calculate" size="18px" class="mb-1" />
                <div>Ingresa talla y peso para calcular IMC</div>
              </div>
            </div>
          </div>

          <!-- Grupo Sanguíneo y Alergias -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <q-select
                v-model="patientForm.blood_type"
                outlined
                dense
                :options="['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'No lo sé']"
                label="Grupo Sanguíneo"
              />
            </div>

            <div>
              <q-input
                v-model="patientForm.allergies"
                outlined
                dense
                label="Alergias a Medicamentos o Sustancias"
                placeholder="Ej. Penicilina, Sulfas, AINEs"
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="teal"
                    label="Ninguna"
                    class="text-2xs font-bold"
                    @click="patientForm.allergies = 'Ninguna conocida'"
                  />
                </template>
              </q-input>
            </div>
          </div>

          <!-- Antecedentes y Medicamentos -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <q-input
                v-model="patientForm.chronic_conditions"
                outlined
                dense
                label="Antecedentes Médicos / Enfermedades Crónicas"
                placeholder="Ej. Hipertensión, Diabetes, Asma, Ninguna"
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="teal"
                    label="Sin antecedentes"
                    class="text-2xs font-bold"
                    @click="patientForm.chronic_conditions = 'Sin antecedentes patológicos'"
                  />
                </template>
              </q-input>
            </div>

            <div>
              <q-input
                v-model="patientForm.current_medications"
                outlined
                dense
                label="Medicamentos que Toma Actualmente"
                placeholder="Ej. Losartán 50mg, Anticonceptivos, Ninguno"
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="teal"
                    label="No toma"
                    class="text-2xs font-bold"
                    @click="patientForm.current_medications = 'No consume medicamentos actualmente'"
                  />
                </template>
              </q-input>
            </div>
          </div>
        </div>
      </div>

      <q-separator />

      <!-- SECCIÓN 3: Selección de Sede/Clínica, Especialista y Fecha -->
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2">
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center">
            <q-icon name="apartment" size="16px" class="mr-1.5 text-teal-600" />
            3. Selecciona Sede / Clínica, Médico y Fecha
          </label>

          <div class="flex items-center space-x-2">
            <!-- Modalidad de búsqueda -->
            <div class="inline-flex rounded-xl bg-slate-100 p-1 border border-slate-200 text-xs">
              <button
                type="button"
                :class="selectionFlow === 'byClinic' ? 'bg-white text-teal-800 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900 font-medium'"
                class="px-3 py-1 rounded-lg transition-all flex items-center"
                @click="setFlow('byClinic')"
              >
                <q-icon name="apartment" size="13px" class="mr-1" />
                <span>Por Clínica</span>
              </button>
              <button
                type="button"
                :class="selectionFlow === 'byDoctor' ? 'bg-white text-teal-800 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900 font-medium'"
                class="px-3 py-1 rounded-lg transition-all flex items-center"
                @click="setFlow('byDoctor')"
              >
                <q-icon name="medical_services" size="13px" class="mr-1" />
                <span>Por Médico</span>
              </button>
            </div>

            <q-btn
              flat
              round
              dense
              icon="refresh"
              color="teal"
              :loading="loadingClinics || loadingDoctors"
              @click="loadInitialData"
            >
              <q-tooltip>Refrescar sedes y especialistas</q-tooltip>
            </q-btn>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- 1. Clínica / Sede -->
          <div>
            <q-select
              v-model="selectedClinicId"
              :options="clinicOptions"
              :loading="loadingClinics"
              no-data-label="No hay sedes disponibles"
              emit-value
              map-options
              outlined
              label="Clínica / Sede de Atención *"
              @update:model-value="onClinicChanged"
            >
              <template v-slot:prepend>
                <q-icon name="apartment" color="teal" />
              </template>
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section avatar>
                    <q-icon name="apartment" color="teal" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="font-medium">{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption class="text-xs text-slate-500">
                      {{ scope.opt.caption || 'Sede de Atención' }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>

          <!-- 2. Especialista Médico -->
          <div>
            <q-select
              v-model="selectedDoctorId"
              :options="doctorOptions"
              :loading="loadingDoctors"
              no-data-label="No se encontraron médicos para esta sede"
              emit-value
              map-options
              outlined
              label="Especialista Médico *"
              @update:model-value="onDoctorChanged"
            >
              <template v-slot:prepend>
                <q-icon name="medical_services" color="teal" />
              </template>
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section avatar>
                    <q-avatar size="28px" color="teal-1" text-color="teal-800" icon="person" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="font-medium">{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption class="text-xs text-slate-500">
                      {{ scope.opt.specialty }} • Atiende en {{ scope.opt.clinicsCount }} sede(s)
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>

          <!-- 3. Fecha de Consulta -->
          <div>
            <q-input
              v-model="selectedDate"
              type="date"
              outlined
              label="Fecha de la Consulta *"
              @update:model-value="loadAvailableSlots"
            >
              <template v-slot:prepend>
                <q-icon name="event" color="teal" />
              </template>
            </q-input>
          </div>
        </div>

        <!-- Feedback contextual -->
        <div v-if="selectedDoctor && selectedClinic" class="p-3.5 bg-teal-50/80 border border-teal-200 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between text-xs text-teal-900 gap-2">
          <div class="flex items-center space-x-2">
            <q-icon name="check_circle" size="18px" color="teal" />
            <span>
              Consultando turnos en <strong>{{ selectedClinic.name }}</strong> con <strong>{{ selectedDoctor.full_name }}</strong> ({{ (Array.isArray(selectedDoctor.specialties) && selectedDoctor.specialties.length > 0) ? selectedDoctor.specialties.join(', ') : (selectedDoctor.specialty || 'Especialista') }}).
            </span>
          </div>
          <div v-if="selectedDoctor.clinics && selectedDoctor.clinics.length > 1" class="text-2xs text-teal-800 bg-teal-100/90 px-2.5 py-1 rounded-full font-semibold self-start sm:self-auto">
            Atiende en {{ selectedDoctor.clinics.length }} sedes
          </div>
        </div>
      </div>

      <q-separator />

      <!-- SECCIÓN 4: Turnos Disponibles (Redis) -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center">
            <q-icon name="schedule" size="16px" class="mr-1.5 text-teal-600" />
            4. Turnos Horarios Disponibles
          </label>
          <span v-if="loadingSlots" class="text-xs text-slate-400 flex items-center">
            <q-spinner size="14px" class="mr-1" /> Calculando disponibilidad...
          </span>
        </div>

        <div v-if="slots.length === 0" class="p-6 bg-slate-50 rounded-2xl border border-slate-200 text-center">
          <q-icon name="schedule" size="32px" class="text-slate-300" />
          <div class="text-xs text-slate-500 mt-2 font-medium">
            No hay turnos disponibles para la fecha seleccionada.
          </div>
          <div class="text-2xs text-slate-400 mt-1">
            Por favor prueba seleccionando otro día o consulta la disponibilidad de otra sede.
          </div>
        </div>

        <div v-else class="space-y-3">
          <!-- Leyenda -->
          <div class="flex items-center space-x-4 text-2xs text-slate-500 font-medium">
            <div class="flex items-center space-x-1.5">
              <span class="w-3 h-3 rounded-md bg-white border border-slate-300 inline-block shadow-2xs"></span>
              <span>Disponible</span>
            </div>
            <div class="flex items-center space-x-1.5">
              <span class="w-3 h-3 rounded-md bg-teal-600 inline-block"></span>
              <span>Seleccionado</span>
            </div>
            <div class="flex items-center space-x-1.5">
              <span class="w-3 h-3 rounded-md bg-slate-200 border border-slate-300 opacity-60 inline-block"></span>
              <span>Ocupado</span>
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
            <button
              type="button"
              v-for="(slot, idx) in slots"
              :key="idx"
              :disabled="!slot.is_available"
              :class="[
                'p-3 rounded-2xl border text-center transition-all font-semibold text-xs select-none',
                !slot.is_available
                  ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed opacity-60'
                  : selectedSlot === slot
                    ? 'bg-teal-600 text-white border-teal-700 shadow-md scale-105 cursor-pointer ring-2 ring-teal-400 ring-offset-1'
                    : 'bg-white hover:bg-teal-50 text-slate-800 border-slate-200 cursor-pointer shadow-2xs'
              ]"
              @click="slot.is_available ? (selectedSlot = slot) : null"
            >
              <div class="flex items-center justify-center space-x-1">
                <span>{{ slot.start_time }}</span>
                <q-icon v-if="!slot.is_available" name="lock" size="12px" class="text-slate-400" />
              </div>
              <div class="text-2xs font-normal" :class="slot.is_available ? 'opacity-75' : 'text-slate-400'">
                {{ slot.is_available ? `a ${slot.end_time}` : 'Ocupado' }}
              </div>
            </button>
          </div>
        </div>
      </div>

      <q-separator />

      <!-- SECCIÓN 5: Honorarios de Consulta Médica -->
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-100 pb-2">
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center">
            <q-icon name="payments" size="16px" class="mr-1.5 text-teal-600" />
            5. Honorarios de Consulta Médica
          </label>
          <span class="text-2xs text-teal-700 bg-teal-50 px-2.5 py-1 rounded-full font-semibold border border-teal-200">
            Pago en taquilla / recepción el día de la cita
          </span>
        </div>

        <!-- Card de Consulta Médica Base -->
        <div class="p-4 bg-teal-50/70 border border-teal-200 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
          <div class="flex items-center space-x-3">
            <div class="w-11 h-11 rounded-xl bg-gradient-to-tr from-teal-600 to-cyan-700 text-white flex items-center justify-center font-bold shadow-xs">
              <q-icon name="health_and_safety" size="22px" />
            </div>
            <div>
              <div class="text-sm font-bold text-slate-900">Consulta Médica Especializada</div>
              <div class="text-xs text-slate-500">
                Atención clínica presencial, anamnesis, evaluación médica integral, diagnóstico y receta digital.
              </div>
            </div>
          </div>
          <div class="text-right sm:border-l sm:border-teal-200 sm:pl-4">
            <div class="text-2xs text-slate-500 uppercase font-semibold">Tarifa Consulta</div>
            <div class="text-xl font-black text-teal-800">${{ Number(doctorConsultationFee).toFixed(2) }} <span class="text-xs font-normal text-slate-500">USD</span></div>
          </div>
        </div>

        <!-- Mensaje Informativo sobre Procedimientos Extra en Consulta -->
        <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-start gap-2.5 text-xs text-slate-600">
          <q-icon name="info" color="teal" size="18px" class="mt-0.5 shrink-0" />
          <div class="leading-relaxed">
            <strong class="text-slate-800">Procedimientos Especializados:</strong>
            Si durante la consulta el especialista determina que requieres estudios o procedimientos adicionales (ecografía, citología, colposcopia, etc.), el médico los indicará y agregará directamente a tu atención para su liquidación en caja.
          </div>
        </div>

        <!-- Total Estimado en Caja -->
        <div class="p-4 bg-slate-900 text-white rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
          <div>
            <div class="text-2xs uppercase tracking-wider text-slate-400 font-bold flex items-center">
              <q-icon name="receipt_long" size="14px" class="mr-1 text-emerald-400" />
              Monto a Liquidar en Sede
            </div>
            <div class="text-xs text-slate-300 mt-0.5">
              Consulta Médica con el especialista seleccionado
            </div>
          </div>
          <div class="text-right sm:border-l sm:border-slate-800 sm:pl-4">
            <div class="text-2xl font-black text-emerald-400">
              ${{ Number(grandTotal).toFixed(2) }} <span class="text-xs font-normal text-slate-400">USD</span>
            </div>
            <div class="text-2xs text-slate-400">Total consulta base</div>
          </div>
        </div>
      </div>

      <q-separator />

      <!-- SECCIÓN 6: Motivo y Confirmación -->
      <div class="space-y-4">
        <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center">
          <q-icon name="comment" size="16px" class="mr-1.5 text-teal-600" />
          6. Motivo Principal de Consulta y Confirmación
        </label>


        <q-input
          v-model="patientForm.reason"
          outlined
          label="Describe brevemente tus síntomas o motivo de la consulta médica *"
          placeholder="Ej. Chequeo preventivo anual, dolor abdominal o pélvico, control de rutina, citología..."
          type="textarea"
          rows="2"
        />

        <div v-if="bookingError" class="p-3 bg-red-50 text-red-700 text-xs rounded-xl flex items-center">
          <q-icon name="warning" size="18px" class="mr-2" />
          <span>{{ bookingError }}</span>
        </div>

        <div class="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div class="text-xs text-slate-500">
            <div v-if="!isLoggedIn" class="flex items-center text-teal-800 font-medium">
              <q-icon name="mark_email_read" size="16px" class="mr-1.5 text-teal-600" />
              Al ser aprobada por el médico, recibirás la invitación a tu correo para activar tu cuenta.
            </div>
            <div v-else class="text-slate-500">
              Garantía de exclusión mutua mediante bloqueo pesimista en MySQL.
            </div>
          </div>

          <q-btn
            color="teal-8"
            icon="check_circle"
            label="Confirmar y Agendar Cita"
            no-caps
            class="px-8 py-3 font-bold text-sm shadow-md rounded-2xl"
            :loading="submitting"
            :disable="!canSubmitBooking"
            @click="submitBooking"
          />
        </div>
      </div>
    </div>

    <!-- Modal Registrar Familiar (Modo Autenticado) -->
    <q-dialog v-model="showAddDependentModal">
      <q-card class="rounded-2xl max-w-lg w-full p-2">
        <q-card-section class="flex items-center justify-between pb-2 border-b border-slate-100">
          <div class="flex items-center space-x-2">
            <div class="w-8 h-8 rounded-lg bg-teal-50 text-teal-800 flex items-center justify-center font-bold">
              <q-icon name="person_add" size="20px" color="teal" />
            </div>
            <h2 class="text-sm font-bold text-slate-900 m-0">
              Registrar Nuevo Familiar
            </h2>
          </div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section class="space-y-4 max-h-[75vh] overflow-y-auto pt-4">
          <!-- Subida de fotografía del familiar (opcional) -->
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center gap-4">
            <div class="w-14 h-14 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-lg overflow-hidden shrink-0 border border-white shadow-xs">
              <img
                v-if="depAvatarDisplayUrl && !depAvatarLoadError"
                :src="depAvatarDisplayUrl"
                class="w-full h-full object-cover"
                alt="Foto"
                @error="depAvatarLoadError = true"
              />
              <span v-else>{{ getInitials(depForm.full_name) }}</span>
            </div>
            <div class="flex-1 space-y-1">
              <div class="text-xs font-bold text-slate-800">
                Fotografía del Familiar <span class="text-slate-400 font-normal text-3xs">(Opcional)</span>
              </div>
              <div class="flex items-center gap-2">
                <input
                  ref="depAvatarInputRef"
                  type="file"
                  accept="image/png, image/jpeg, image/webp"
                  class="hidden"
                  @change="handleDepAvatarFileSelect"
                />
                <q-btn
                  unelevated
                  dense
                  size="xs"
                  color="teal-8"
                  icon="photo_camera"
                  :label="depAvatarDisplayUrl ? 'Cambiar Foto' : 'Subir Foto'"
                  no-caps
                  class="px-2 py-1 font-semibold"
                  @click="triggerDepAvatarUpload"
                />
                <q-btn
                  v-if="depAvatarPreview"
                  flat
                  dense
                  size="xs"
                  color="negative"
                  icon="delete"
                  label="Quitar"
                  no-caps
                  class="px-2 py-1 font-semibold"
                  @click="clearDepAvatar"
                />
                <span class="text-3xs text-slate-400">JPG, PNG o WEBP (máx. 5MB)</span>
              </div>
            </div>
          </div>

          <!-- 1. Datos de Identidad -->
          <div class="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-1 flex items-center">
            <q-icon name="badge" size="14px" class="mr-1 text-teal-600" />
            1. Datos de Identidad
          </div>

          <div class="space-y-3">
            <q-input
              v-model="depForm.full_name"
              outlined
              dense
              label="Nombre y Apellido del Familiar *"
              placeholder="Ej. Sofía Pérez"
              :rules="[val => !!val || 'El nombre es obligatorio']"
            />

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <q-select
                v-model="depForm.relationship"
                outlined
                dense
                :options="relationshipOptions"
                emit-value
                map-options
                label="Parentesco o Relación *"
                :rules="[val => !!val || 'El parentesco es obligatorio']"
              />

              <q-input
                v-model="depForm.birth_date"
                outlined
                dense
                type="date"
                label="Fecha de Nacimiento *"
                :rules="[val => !!val || 'La fecha es obligatoria']"
              />
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <q-select
                v-model="depForm.gender"
                outlined
                dense
                :options="['Femenino', 'Masculino', 'Otro']"
                label="Sexo Biológico"
              />

              <q-input
                v-model="depForm.id_document"
                outlined
                dense
                label="Documento de Identidad / Cédula"
                placeholder="Ej. V-32111222"
              />
            </div>

            <q-input
              v-model="depForm.phone"
              outlined
              dense
              label="Teléfono del Familiar (opcional)"
              placeholder="Ej. +58 412 1234567"
            />
          </div>

          <!-- 2. Ficha Clínica Basal Permanente -->
          <div class="text-xs font-bold uppercase tracking-wider text-teal-800 border-b border-teal-100 pb-1 pt-2 flex items-center">
            <q-icon name="monitor_heart" size="14px" class="mr-1 text-teal-600" />
            2. Ficha Clínica Permanente del Familiar
          </div>

          <div class="space-y-3">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <q-select
                v-model="depForm.blood_type"
                outlined
                dense
                :options="['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'No lo sé']"
                label="Grupo Sanguíneo"
              >
                <template #prepend>
                  <q-icon name="bloodtype" color="red-6" size="18px" />
                </template>
              </q-select>

              <q-input
                v-model.number="depForm.height_cm"
                outlined
                dense
                type="number"
                label="Estatura / Talla (cm)"
                placeholder="Ej. 130"
                suffix="cm"
                :rules="[val => !val || (val >= 20 && val <= 250) || 'Talla debe ser entre 20 y 250 cm']"
              />
            </div>

            <q-input
              v-model="depForm.allergies"
              outlined
              dense
              label="Alergias Conocidas"
              placeholder="Ej. Amoxicilina, Maní, Ninguna"
            >
              <template #append>
                <q-btn
                  flat
                  dense
                  no-caps
                  color="teal"
                  label="Ninguna"
                  class="text-2xs font-bold"
                  @click="depForm.allergies = 'Ninguna conocida'"
                />
              </template>
            </q-input>

            <q-input
              v-model="depForm.chronic_conditions"
              outlined
              dense
              label="Antecedentes Médicos / Enfermedades"
              placeholder="Ej. Asma, Dermatitis, Ninguna"
            >
              <template #append>
                <q-btn
                  flat
                  dense
                  no-caps
                  color="teal"
                  label="Sin antecedentes"
                  class="text-2xs font-bold"
                  @click="depForm.chronic_conditions = 'Sin antecedentes patológicos'"
                />
              </template>
            </q-input>

            <q-input
              v-model="depForm.notes"
              outlined
              dense
              type="textarea"
              rows="2"
              label="Notas Clínicas / Observaciones Especiales"
              placeholder="Observaciones para el médico especialista durante su consulta..."
            />
          </div>
        </q-card-section>

        <q-card-actions align="right" class="p-3 bg-slate-50 border-t border-slate-100">
          <q-btn flat label="Cancelar" color="slate-7" no-caps v-close-popup />
          <q-btn
            unelevated
            color="primary"
            label="Guardar Familiar"
            :loading="savingDependent"
            no-caps
            class="font-bold text-xs px-4 py-2 shadow-xs"
            @click="saveDependent"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Diálogo de Éxito para Agendamiento Público -->
    <q-dialog v-model="showSuccessModal" persistent>
      <q-card class="max-w-md w-full rounded-3xl overflow-hidden shadow-2xl p-6 md:p-8 text-center space-y-5">
        <div class="w-16 h-16 rounded-3xl bg-teal-50 text-teal-700 flex items-center justify-center mx-auto shadow-inner">
          <q-icon name="mark_email_read" size="36px" />
        </div>

        <div>
          <h2 class="text-xl font-bold text-slate-900">¡Cita Médica Registrada!</h2>
          <p class="text-xs text-slate-500 mt-1">
            Tu turno con el <strong>{{ selectedDoctor?.full_name || 'Médico Especialista' }}</strong> ha sido reservado.
          </p>
        </div>

        <div class="bg-teal-50/70 border border-teal-200/80 rounded-2xl p-4 text-xs text-teal-950 text-left space-y-2">
          <div class="flex items-center text-teal-800 font-bold">
            <q-icon name="info" size="16px" class="mr-1.5 text-teal-600" />
            <span>Próximos Pasos:</span>
          </div>
          <p class="text-slate-700 leading-relaxed">
            El especialista revisará tus datos de triage y medidas para confirmar la consulta. En cuanto sea aprobada, recibirás un correo en <strong>{{ patientForm.email }}</strong> con tu enlace para activar tu cuenta en <strong>VitaRecord</strong>.
          </p>
          <div class="text-2xs text-slate-500 bg-white p-2.5 rounded-xl border border-teal-100">
            Con tu cuenta de VitaRecord podrás descargar tus <strong>recetas médicas electrónicas con código QR</strong>, acceder a tus informes y consultar tu historial clínico en cualquier momento.
          </div>
        </div>

        <div class="flex flex-col gap-2 pt-2">
          <q-btn
            color="teal-8"
            label="Entendido, Ir al Directorio Médico"
            to="/doctors"
            no-caps
            class="w-full py-2.5 font-bold rounded-xl shadow-xs"
          />
          <q-btn
            flat
            color="slate-600"
            label="Volver al Inicio"
            to="/"
            no-caps
            class="text-xs font-semibold"
          />
        </div>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Notify } from 'quasar'
import { api } from 'boot/axios'
import { useAcl } from 'src/composables/useAcl'

const route = useRoute()
const router = useRouter()
const { isLoggedIn } = useAcl()

// Estado de Beneficiario (solo usado si está logueado)
const beneficiaryType = ref('self')
const selectedDependentId = ref(null)
const dependents = ref([])
const loadingDependents = ref(false)
const showAddDependentModal = ref(false)
const showSuccessModal = ref(false)
const savingDependent = ref(false)

const relationshipOptions = [
  { label: 'Hijo / Hija', value: 'HIJO' },
  { label: 'Cónyuge / Pareja', value: 'CONYUGE' },
  { label: 'Madre / Padre', value: 'PADRE' },
  { label: 'Hermano / Hermana', value: 'HERMANO' },
  { label: 'Otro Familiar / Tutor', value: 'OTRO' }
]

const depForm = reactive({
  full_name: '',
  relationship: 'HIJO',
  birth_date: '',
  id_document: '',
  gender: 'Femenino',
  phone: '',
  blood_type: 'O+',
  height_cm: null,
  allergies: '',
  chronic_conditions: '',
  notes: ''
})

const depAvatarInputRef = ref(null)
const depAvatarFile = ref(null)
const depAvatarPreview = ref(null)
const depAvatarLoadError = ref(false)

const depAvatarDisplayUrl = computed(() => {
  return depAvatarPreview.value || null
})

function getInitials (name) {
  if (!name) return 'F'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

function triggerDepAvatarUpload () {
  if (depAvatarInputRef.value) {
    depAvatarInputRef.value.click()
  }
}

function handleDepAvatarFileSelect (event) {
  const file = event.target.files?.[0]
  if (!file) return

  if (file.size > 5 * 1024 * 1024) {
    Notify.create({ type: 'negative', message: 'La imagen excede el límite permitido de 5 MB.' })
    if (event.target) event.target.value = ''
    return
  }

  depAvatarFile.value = file
  if (depAvatarPreview.value) {
    URL.revokeObjectURL(depAvatarPreview.value)
  }
  depAvatarPreview.value = URL.createObjectURL(file)
  depAvatarLoadError.value = false
  if (event.target) {
    event.target.value = ''
  }
}

function clearDepAvatar () {
  if (depAvatarPreview.value) {
    URL.revokeObjectURL(depAvatarPreview.value)
  }
  depAvatarPreview.value = null
  depAvatarFile.value = null
  depAvatarLoadError.value = false
}

function openQuickAddDependentModal () {
  clearDepAvatar()
  depForm.full_name = ''
  depForm.relationship = 'HIJO'
  depForm.birth_date = ''
  depForm.id_document = ''
  depForm.gender = 'Femenino'
  depForm.phone = ''
  depForm.blood_type = 'O+'
  depForm.height_cm = null
  depForm.allergies = ''
  depForm.chronic_conditions = ''
  depForm.notes = ''
  showAddDependentModal.value = true
}

// Honorarios de Consulta Médica
const doctorConsultationFee = ref(30.00)

const grandTotal = computed(() => {
  return Number(doctorConsultationFee.value || 30.00)
})

async function loadDoctorFee () {
  if (!selectedClinicId.value || !selectedDoctorId.value) {
    doctorConsultationFee.value = 30.00
    return
  }
  try {
    const { data: clinicDocs } = await api.get(`/clinics/${selectedClinicId.value}/doctors`)
    const docInfo = (clinicDocs || []).find(d => d.id === selectedDoctorId.value)
    if (docInfo && docInfo.consultation_fee != null) {
      doctorConsultationFee.value = parseFloat(docInfo.consultation_fee)
    } else {
      doctorConsultationFee.value = 30.00
    }
  } catch (err) {
    console.warn('Error al cargar honorarios de consulta:', err)
  }
}


// Perfil permanente del paciente
const patientProfile = ref(null)

const selectedDependent = computed(() => {
  return dependents.value.find(d => d.id === selectedDependentId.value)
})

const hasPermanentClinicalData = computed(() => {
  if (!isLoggedIn.value) return false
  if (beneficiaryType.value === 'self') {
    return !!(
      patientProfile.value &&
      patientProfile.value.blood_type &&
      patientProfile.value.height_cm
    )
  }
  if (beneficiaryType.value === 'dependent') {
    const dep = selectedDependent.value
    return !!(
      dep &&
      dep.blood_type &&
      dep.height_cm
    )
  }
  return false
})

// Formulario unificado de paciente y triage (público y logueado)
const patientForm = reactive({
  full_name: '',
  id_document: '',
  email: '',
  phone: '',
  birth_date: '',
  gender: 'Femenino',
  country: 'Venezuela',
  city: '',
  address: '',
  height_cm: null,
  weight_kg: null,
  blood_type: 'O+',
  allergies: '',
  chronic_conditions: '',
  current_medications: '',
  reason: ''
})

// Cálculo en vivo del IMC
const calculatedBmi = computed(() => {
  if (patientForm.height_cm && patientForm.weight_kg && patientForm.height_cm > 0) {
    const hM = patientForm.height_cm / 100
    return (patientForm.weight_kg / (hM * hM)).toFixed(1)
  }
  return null
})

const bmiCategoryText = computed(() => {
  const bmi = parseFloat(calculatedBmi.value)
  if (!bmi) return ''
  if (bmi < 18.5) return 'Bajo peso'
  if (bmi < 25.0) return 'Peso normal'
  if (bmi < 30.0) return 'Sobrepeso'
  return 'Obesidad'
})

const bmiCategoryClass = computed(() => {
  const bmi = parseFloat(calculatedBmi.value)
  if (!bmi) return ''
  if (bmi < 18.5) return 'bg-amber-100 text-amber-800'
  if (bmi < 25.0) return 'bg-teal-100 text-teal-800'
  if (bmi < 30.0) return 'bg-orange-100 text-orange-800'
  return 'bg-red-100 text-red-800'
})

// Flujo de Selección de Sede / Especialista
const selectionFlow = ref('byDoctor') // 'byClinic' | 'byDoctor'

// Estado Clínicas y Médicos
const clinics = ref([])
const allDoctors = ref([])
function getDefaultBookingDate () {
  const now = new Date()
  if (now.getDay() === 0) {
    now.setDate(now.getDate() + 1)
  }
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const selectedClinicId = ref(null)
const selectedDoctorId = ref(null)
const selectedDate = ref(getDefaultBookingDate())
const slots = ref([])
const selectedSlot = ref(null)

const loadingClinics = ref(false)
const loadingDoctors = ref(false)
const loadingSlots = ref(false)
const submitting = ref(false)
const bookingError = ref('')

function setFlow (flow) {
  selectionFlow.value = flow
}

const selectedDoctor = computed(() => {
  return allDoctors.value.find(d => d.id === selectedDoctorId.value) || null
})

const selectedClinic = computed(() => {
  return clinics.value.find(c => c.id === selectedClinicId.value) || null
})

const clinicOptions = computed(() => {
  let list = clinics.value
  if (selectionFlow.value === 'byDoctor' && selectedDoctor.value?.clinics?.length) {
    list = selectedDoctor.value.clinics
  }
  const seen = new Set()
  const unique = []
  for (const c of list) {
    if (c?.id && !seen.has(c.id)) {
      seen.add(c.id)
      unique.push(c)
    }
  }
  return unique.map(c => ({
    label: c.name,
    value: c.id,
    caption: `${c.timezone || 'America/Caracas'} • ${c.country_code || 'VE'}`
  }))
})

const doctorOptions = computed(() => {
  let list = allDoctors.value
  if (selectionFlow.value === 'byClinic' && selectedClinicId.value) {
    list = allDoctors.value.filter(d => (d.clinics || []).some(c => c.id === selectedClinicId.value))
  }
  const seen = new Set()
  const unique = []
  for (const d of list) {
    if (d?.id && !seen.has(d.id)) {
      seen.add(d.id)
      unique.push(d)
    }
  }
  return unique.map(d => ({
    label: `${d.full_name || d.email}`,
    specialties: d.specialties || [],
    specialty: (Array.isArray(d.specialties) && d.specialties.length > 0)
      ? d.specialties.join(', ')
      : (d.specialty || 'Medicina Especializada'),
    clinicsCount: (d.clinics || []).length,
    value: d.id
  }))
})

const dependentOptions = computed(() => {
  return dependents.value.map(d => ({
    label: `${d.full_name} (${d.relationship})`,
    value: d.id
  }))
})

const canSubmitBooking = computed(() => {
  if (!selectedSlot.value || !selectedSlot.value.is_available) return false
  if (!isLoggedIn.value) {
    return (
      patientForm.full_name.trim().length >= 3 &&
      patientForm.email.trim().length >= 5 &&
      patientForm.phone.trim().length >= 7 &&
      patientForm.id_document.trim().length >= 4
    )
  }
  return true
})

async function onClinicChanged (newClinicId) {
  selectedClinicId.value = newClinicId
  if (selectionFlow.value === 'byClinic') {
    const validDoctor = doctorOptions.value.some(d => d.value === selectedDoctorId.value)
    if (!validDoctor && doctorOptions.value.length > 0) {
      selectedDoctorId.value = doctorOptions.value[0].value
    }
  }
  await Promise.all([loadAvailableSlots(), loadDoctorFee()])
}

async function onDoctorChanged (newDoctorId) {
  selectedDoctorId.value = newDoctorId
  if (selectionFlow.value === 'byDoctor') {
    const doc = allDoctors.value.find(d => d.id === newDoctorId)
    if (doc?.clinics?.length) {
      const validClinic = doc.clinics.some(c => c.id === selectedClinicId.value)
      if (!validClinic) {
        selectedClinicId.value = doc.clinics[0].id
      }
    }
  }
  await Promise.all([loadAvailableSlots(), loadDoctorFee()])
}

async function loadInitialData () {
  loadingClinics.value = true
  loadingDoctors.value = true
  try {
    const [clinicsRes, doctorsRes] = await Promise.all([
      api.get('/clinics/public', { params: { _t: Date.now() } }),
      api.get('/doctors/public-directory', { params: { _t: Date.now() } })
    ])
    clinics.value = clinicsRes.data
    allDoctors.value = doctorsRes.data

    const queryDoctorId = route.query?.doctor_id
    const queryClinicId = route.query?.clinic_id

    if (queryDoctorId && allDoctors.value.some(d => d.id === queryDoctorId)) {
      selectedDoctorId.value = queryDoctorId
      selectionFlow.value = 'byDoctor'

      const targetDoc = allDoctors.value.find(d => d.id === queryDoctorId)
      if (queryClinicId && clinics.value.some(c => c.id === queryClinicId)) {
        selectedClinicId.value = queryClinicId
      } else if (targetDoc?.clinics?.length) {
        selectedClinicId.value = targetDoc.clinics[0].id
      }
    } else {
      if (queryClinicId && clinics.value.some(c => c.id === queryClinicId)) {
        selectedClinicId.value = queryClinicId
      } else if (clinics.value.length > 0) {
        selectedClinicId.value = clinics.value[0].id
      }

      if (allDoctors.value.length > 0 && !selectedDoctorId.value) {
        const docsInClinic = allDoctors.value.filter(d => (d.clinics || []).some(c => c.id === selectedClinicId.value))
        selectedDoctorId.value = docsInClinic.length > 0 ? docsInClinic[0].id : allDoctors.value[0].id
      }
    }

    if (isLoggedIn.value) {
      try {
        const { data: pData } = await api.get('/patients/me/profile')
        patientProfile.value = pData
        if (pData.full_name && !patientForm.full_name) patientForm.full_name = pData.full_name
        if (pData.email && !patientForm.email) patientForm.email = pData.email
        if (pData.phone && !patientForm.phone) patientForm.phone = pData.phone
        if (pData.identification_number && !patientForm.id_document) patientForm.id_document = pData.identification_number
        if (pData.blood_type) patientForm.blood_type = pData.blood_type
        if (pData.height_cm != null) patientForm.height_cm = Number(pData.height_cm)
        if (pData.allergies) patientForm.allergies = pData.allergies
        if (pData.chronic_conditions) patientForm.chronic_conditions = pData.chronic_conditions
        if (pData.country) patientForm.country = pData.country
        if (pData.city) patientForm.city = pData.city
        if (pData.address) patientForm.address = pData.address
        if (pData.gender) patientForm.gender = pData.gender
        if (pData.birth_date) {
          patientForm.birth_date = typeof pData.birth_date === 'string' ? pData.birth_date.substring(0, 10) : ''
        }
      } catch (err) {
        console.warn('No se pudo precargar perfil de paciente:', err)
      }
      await fetchDependents()
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al consultar clínicas y médicos disponibles.' })
  } finally {
    loadingClinics.value = false
    loadingDoctors.value = false
    await Promise.all([loadAvailableSlots(), loadDoctorFee()])
  }
}

function selectSelf () {
  beneficiaryType.value = 'self'
  selectedDependentId.value = null
  if (patientProfile.value) {
    if (patientProfile.value.full_name) patientForm.full_name = patientProfile.value.full_name
    if (patientProfile.value.email) patientForm.email = patientProfile.value.email
    if (patientProfile.value.phone) patientForm.phone = patientProfile.value.phone
    if (patientProfile.value.identification_number) patientForm.id_document = patientProfile.value.identification_number
    if (patientProfile.value.blood_type) patientForm.blood_type = patientProfile.value.blood_type
    if (patientProfile.value.height_cm != null) patientForm.height_cm = Number(patientProfile.value.height_cm)
    if (patientProfile.value.allergies) patientForm.allergies = patientProfile.value.allergies
    if (patientProfile.value.chronic_conditions) patientForm.chronic_conditions = patientProfile.value.chronic_conditions
    if (patientProfile.value.gender) patientForm.gender = patientProfile.value.gender
    if (patientProfile.value.birth_date) {
      patientForm.birth_date = typeof patientProfile.value.birth_date === 'string' ? patientProfile.value.birth_date.substring(0, 10) : ''
    }
  }
}

function applySelectedDependent () {
  const dep = dependents.value.find(d => d.id === selectedDependentId.value)
  if (dep) {
    if (dep.full_name) patientForm.full_name = dep.full_name
    if (dep.id_document) patientForm.id_document = dep.id_document
    patientForm.blood_type = dep.blood_type || ''
    patientForm.height_cm = dep.height_cm != null ? Number(dep.height_cm) : null
    patientForm.allergies = dep.allergies || ''
    patientForm.chronic_conditions = dep.chronic_conditions || ''
    if (dep.gender) patientForm.gender = dep.gender
    if (dep.birth_date) {
      patientForm.birth_date = typeof dep.birth_date === 'string' ? dep.birth_date.substring(0, 10) : ''
    }
  }
}

function selectDependentMode () {
  beneficiaryType.value = 'dependent'
  if (dependents.value.length > 0 && !selectedDependentId.value) {
    selectedDependentId.value = dependents.value[0].id
  }
  applySelectedDependent()
}

watch(selectedDependentId, () => {
  if (beneficiaryType.value === 'dependent') {
    applySelectedDependent()
  }
})

async function fetchDependents () {
  loadingDependents.value = true
  try {
    const { data } = await api.get('/patients/me/dependents')
    dependents.value = data || []
    if (beneficiaryType.value === 'dependent' && dependents.value.length > 0 && !selectedDependentId.value) {
      selectedDependentId.value = dependents.value[0].id
    }
    if (beneficiaryType.value === 'dependent') {
      applySelectedDependent()
    }
  } catch (err) {
    // Si no está autenticado o error, silenciar
  } finally {
    loadingDependents.value = false
  }
}

async function saveDependent () {
  if (!depForm.full_name || !depForm.birth_date) {
    Notify.create({
      type: 'warning',
      message: 'Por favor completa el nombre y la fecha de nacimiento.'
    })
    return
  }

  savingDependent.value = true
  try {
    const payload = {
      full_name: depForm.full_name.trim(),
      relationship: depForm.relationship,
      birth_date: depForm.birth_date,
      gender: depForm.gender,
      id_document: depForm.id_document?.trim() || undefined,
      phone: depForm.phone?.trim() || undefined,
      blood_type: depForm.blood_type || undefined,
      height_cm: depForm.height_cm != null ? Number(depForm.height_cm) : undefined,
      allergies: depForm.allergies?.trim() || undefined,
      chronic_conditions: depForm.chronic_conditions?.trim() || undefined,
      notes: depForm.notes?.trim() || undefined
    }

    const { data } = await api.post('/patients/me/dependents', payload)
    if (depAvatarFile.value && data?.id) {
      try {
        const formData = new FormData()
        formData.append('file', depAvatarFile.value)
        await api.post(`/patients/me/dependents/${data.id}/avatar`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      } catch (uploadErr) {
        console.error('Error al subir fotografía del nuevo familiar:', uploadErr)
      }
    }
    clearDepAvatar()
    Notify.create({ type: 'positive', message: '¡Familiar registrado con éxito!' })
    showAddDependentModal.value = false
    await fetchDependents()
    selectedDependentId.value = data.id
    applySelectedDependent()
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al guardar familiar.'
    })
  } finally {
    savingDependent.value = false
  }
}

async function loadAvailableSlots () {
  if (!selectedClinicId.value || !selectedDoctorId.value || !selectedDate.value) {
    slots.value = []
    return
  }
  loadingSlots.value = true
  selectedSlot.value = null
  bookingError.value = ''
  try {
    const { data } = await api.get(`/clinics/${selectedClinicId.value}/doctors/${selectedDoctorId.value}/slots?date=${selectedDate.value}`)
    slots.value = data
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al consultar disponibilidad de turnos.' })
  } finally {
    loadingSlots.value = false
  }
}

async function submitBooking () {
  if (!canSubmitBooking.value) return
  submitting.value = true
  bookingError.value = ''

  try {
    const startIso = `${selectedDate.value}T${selectedSlot.value.start_time}:00`
    const endIso = `${selectedDate.value}T${selectedSlot.value.end_time}:00`

    if (!isLoggedIn.value) {
      // Flujo de agendamiento público sin sesión
      const publicPayload = {
        clinic_id: selectedClinicId.value,
        doctor_id: selectedDoctorId.value,
        start_time: startIso,
        end_time: endIso,
        full_name: patientForm.full_name,
        email: patientForm.email,
        phone: patientForm.phone,
        id_document: patientForm.id_document || undefined,
        birth_date: patientForm.birth_date || undefined,
        gender: patientForm.gender || undefined,
        country: patientForm.country || 'Venezuela',
        city: patientForm.city || undefined,
        address: patientForm.address || undefined,
        height_cm: patientForm.height_cm || undefined,
        weight_kg: patientForm.weight_kg || undefined,
        blood_type: patientForm.blood_type || undefined,
        allergies: patientForm.allergies || undefined,
        chronic_conditions: patientForm.chronic_conditions || undefined,
        current_medications: patientForm.current_medications || undefined,
        reason: patientForm.reason || undefined,
        procedure_ids: [],
        estimated_amount: grandTotal.value
      }

      await api.post('/appointments/public-book', publicPayload)
      showSuccessModal.value = true
    } else {
      // Flujo autenticado estándar
      const payload = {
        clinic_id: selectedClinicId.value,
        doctor_id: selectedDoctorId.value,
        dependent_id: beneficiaryType.value === 'dependent' ? selectedDependentId.value : undefined,
        start_time: startIso,
        end_time: endIso,
        reason: patientForm.reason || undefined,
        intake_data: {
          height_cm: patientForm.height_cm,
          weight_kg: patientForm.weight_kg,
          bmi: calculatedBmi.value ? parseFloat(calculatedBmi.value) : undefined,
          bmi_category: bmiCategoryText.value,
          blood_type: patientForm.blood_type,
          allergies: patientForm.allergies,
          chronic_conditions: patientForm.chronic_conditions,
          current_medications: patientForm.current_medications
        },
        procedure_ids: [],
        estimated_amount: grandTotal.value
      }

      await api.post('/appointments', payload)
      Notify.create({
        type: 'positive',
        message: '¡Cita médica agendada exitosamente!'
      })
      router.push('/appointments/my-list')
    }
  } catch (err) {
    bookingError.value = err.response?.data?.detail || err.message || 'No se pudo completar la reserva de la cita.'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {

  await loadInitialData()
})
</script>
