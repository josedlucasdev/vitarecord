<template>
  <q-page class="p-4 md:p-8 bg-slate-50 min-h-screen">
    <div class="max-w-5xl mx-auto space-y-6">
      <!-- Encabezado de la Consulta -->
      <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-xl font-bold text-slate-900 leading-tight">Consulta Médica Especializada</h1>
          <p class="text-xs text-slate-500">Expediente Clínico Electrónico cifrado con AES-256-GCM y Receta con QR</p>
        </div>
        <q-btn
          flat
          dense
          color="slate-600"
          icon="arrow_back"
          label="Volver a Citas"
          no-caps
          to="/appointments/my-list"
          class="self-start md:self-auto text-xs"
        />
      </div>

      <!-- Spinner de Carga de la Cita -->
      <div v-if="loadingAppointment" class="p-12 text-center bg-white rounded-2xl border border-slate-200">
        <q-spinner-dots color="teal" size="48px" />
        <p class="text-slate-500 text-xs mt-3">Cargando expediente de la cita...</p>
      </div>

      <div v-else-if="!appointment" class="p-8 text-center bg-white rounded-2xl border border-red-200">
        <q-icon name="warning" size="40px" color="negative" />
        <h2 class="text-base font-bold text-slate-800 mt-2">Cita no encontrada</h2>
        <p class="text-xs text-slate-500 mt-1">Por favor selecciona una cita válida desde la lista de gestión.</p>
        <q-btn color="primary" label="Ir a Mis Citas" no-caps to="/appointments/my-list" class="mt-4" />
      </div>

      <!-- Formulario de Consulta -->
      <form v-else @submit.prevent="submitConsultation" class="space-y-6">
        <!-- 1. Tarjeta de Datos del Paciente -->
        <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
              <q-icon name="person" size="18px" class="mr-2 text-teal-600" />
              1. Identificación del Paciente
            </h2>
            <q-badge color="teal-1" text-color="teal-9" class="font-semibold text-xs py-1 px-2.5">
              Estado: {{ appointment.status }}
            </q-badge>
          </div>

          <!-- Si es familiar dependiente, destacar al paciente atendido y al titular responsable -->
          <div v-if="appointment.dependent_id" class="p-4 bg-teal-50/70 rounded-xl border border-teal-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div class="flex items-center space-x-3">
              <div class="w-11 h-11 rounded-xl bg-teal-600 text-white flex items-center justify-center shrink-0 shadow-2xs">
                <q-icon name="family_restroom" size="24px" />
              </div>
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-xs font-bold uppercase text-teal-800 tracking-wider">Paciente en Consulta (Familiar):</span>
                  <q-badge color="teal-8" text-color="white" class="font-bold text-2xs py-0.5 px-2">
                    {{ appointment.dependent_relationship || 'Familiar Dependiente' }}
                  </q-badge>
                  <q-badge outline color="teal-9" class="font-semibold text-3xs">
                    🔒 Expediente Clínico Separado
                  </q-badge>
                </div>
                <div class="text-base font-bold text-slate-900 mt-0.5">
                  {{ appointment.dependent_name || 'Familiar Dependiente' }}
                </div>
              </div>
            </div>
            <div class="text-2xs text-slate-600 bg-white/90 p-2.5 rounded-lg border border-teal-100 flex flex-col justify-center">
              <span class="text-slate-400 font-semibold">Titular / Representante:</span>
              <span class="font-bold text-slate-800">{{ appointment.patient_name }}</span>
              <span v-if="appointment.patient_phone" class="text-slate-500">Tel: {{ appointment.patient_phone }}</span>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div v-if="!appointment.dependent_id" class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div class="text-slate-400 font-medium">Paciente Titular:</div>
              <div class="font-bold text-slate-800 mt-0.5 text-sm">{{ appointment.patient_name || 'Paciente' }}</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div class="text-slate-400 font-medium">Modalidad:</div>
              <div class="font-bold text-slate-800 mt-0.5 text-sm">
                {{ appointment.dependent_id ? 'Familiar a Cargo' : 'Titular Directo' }}
              </div>
            </div>
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div class="text-slate-400 font-medium">Sede Clínica:</div>
              <div class="font-bold text-slate-800 mt-0.5 text-sm">{{ appointment.clinic_name || 'Sede Principal' }}</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div class="text-slate-400 font-medium">Fecha y Turno:</div>
              <div class="font-bold text-slate-800 mt-0.5 text-sm">
                {{ formatDateTime(appointment.start_time) }}
              </div>
            </div>
          </div>

          <div v-if="appointment.reason" class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start">
            <q-icon name="info" size="16px" class="mr-2 mt-0.5 text-amber-600" />
            <div>
              <span class="font-bold">Motivo reportado al agendar:</span> "{{ appointment.reason }}"
            </div>
          </div>

          <!-- Medidas de Triage y Antecedentes reportados al agendar -->
          <div v-if="appointment.intake_data && Object.keys(appointment.intake_data).length > 0" class="p-4 bg-teal-50/70 border border-teal-200/80 rounded-xl space-y-2 text-xs">
            <div class="flex items-center justify-between text-teal-800 font-bold uppercase tracking-wide text-2xs">
              <div class="flex items-center">
                <q-icon name="monitor_heart" size="14px" class="mr-1 text-teal-600" />
                Triage Clínico y Ficha Basal de {{ appointment.dependent_id ? (appointment.dependent_name || 'Familiar') : appointment.patient_name }}
              </div>
              <span class="text-3xs font-medium lowercase text-teal-700">Ficha clínica individual</span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-slate-700">
              <div class="bg-white p-2.5 rounded-lg border border-teal-100">
                <span class="text-2xs text-slate-400 block font-semibold">Talla:</span>
                <span class="font-bold text-slate-800">{{ appointment.intake_data.height_cm ? `${appointment.intake_data.height_cm} cm` : 'N/D' }}</span>
              </div>
              <div class="bg-white p-2.5 rounded-lg border border-teal-100">
                <span class="text-2xs text-slate-400 block font-semibold">Peso:</span>
                <span class="font-bold text-slate-800">{{ appointment.intake_data.weight_kg ? `${appointment.intake_data.weight_kg} kg` : 'N/D' }}</span>
              </div>
              <div class="bg-white p-2.5 rounded-lg border border-teal-100">
                <span class="text-2xs text-slate-400 block font-semibold">IMC:</span>
                <span class="font-bold text-slate-800">{{ appointment.intake_data.bmi || 'N/D' }} {{ appointment.intake_data.bmi_category ? `(${appointment.intake_data.bmi_category})` : '' }}</span>
              </div>
              <div class="bg-white p-2.5 rounded-lg border border-teal-100">
                <span class="text-2xs text-slate-400 block font-semibold">Grupo Sanguíneo:</span>
                <span class="font-bold text-slate-800">{{ appointment.intake_data.blood_type || 'N/D' }}</span>
              </div>
            </div>
            <div class="flex flex-wrap gap-2 pt-1 text-2xs">
              <span v-if="appointment.intake_data.allergies" class="bg-red-50 text-red-800 border border-red-200 px-2 py-0.5 rounded-md font-medium">
                <strong>Alergias:</strong> {{ appointment.intake_data.allergies }}
              </span>
              <span v-if="appointment.intake_data.chronic_conditions" class="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md font-medium">
                <strong>Antecedentes:</strong> {{ appointment.intake_data.chronic_conditions }}
              </span>
              <span v-if="appointment.intake_data.current_medications" class="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md font-medium">
                <strong>Medicación:</strong> {{ appointment.intake_data.current_medications }}
              </span>
            </div>
          </div>

          <!-- Acceso Directo al Historial Clínico Completo -->
          <div class="p-3.5 bg-teal-50/60 border border-teal-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div class="flex items-center space-x-2.5 text-slate-700">
              <q-icon name="folder_shared" size="22px" class="text-teal-700 shrink-0" />
              <div>
                <div class="font-bold text-slate-900 flex items-center gap-1.5">
                  <span>Historial de {{ appointment.dependent_id ? (appointment.dependent_name || 'Familiar') : appointment.patient_name }}:</span>
                  <q-badge color="teal-1" text-color="teal-9" class="font-semibold text-3xs">
                    {{ appointment.dependent_id ? 'Expediente del Familiar' : 'Expediente del Titular' }}
                  </q-badge>
                </div>
                <div class="text-2xs text-slate-600 mt-0.5">
                  <span>{{ patientHistory.length }} consulta{{ patientHistory.length !== 1 ? 's' : '' }} previa{{ patientHistory.length !== 1 ? 's' : '' }}</span>
                  <span v-if="activeTreatments.length > 0" class="text-amber-900 font-bold ml-1.5">
                    • ⚠️ {{ activeTreatments.length }} tratamiento{{ activeTreatments.length !== 1 ? 's' : '' }} activo{{ activeTreatments.length !== 1 ? 's' : '' }}
                  </span>
                  <span v-else class="text-emerald-700 font-medium ml-1.5">
                    • Sin tratamientos activos vigentes
                  </span>
                </div>
              </div>
            </div>
            <q-btn
              color="teal-8"
              icon="open_in_new"
              :label="'Ver Expediente de ' + (appointment.dependent_id ? (appointment.dependent_name || 'Familiar') : 'Paciente')"
              no-caps
              dense
              class="text-xs px-3 py-1.5 font-bold shadow-xs self-start sm:self-auto"
              @click="showHistoryDialog = true"
            />
          </div>
        </div>

        <!-- Resumen si la Cita ya fue Completada Previamente -->
        <div v-if="appointment.status === 'COMPLETED'" class="bg-white p-6 rounded-2xl shadow-xs border border-emerald-200 space-y-4">
          <div class="flex items-center justify-between border-b border-emerald-100 pb-3">
            <div class="flex items-center space-x-2 text-emerald-800 font-bold text-sm uppercase tracking-wider">
              <q-icon name="verified" size="20px" class="text-emerald-600" />
              <span>Consulta Finalizada y Firmada Electrónicamente</span>
            </div>
            <q-badge color="emerald-1" text-color="emerald-9" class="font-bold text-xs py-1 px-2.5">
              COMPLETED
            </q-badge>
          </div>

          <div v-if="loadingAppointmentRecord" class="p-6 text-center">
            <q-spinner-dots color="teal" size="36px" />
            <p class="text-xs text-slate-500 mt-2">Cargando expediente de esta consulta...</p>
          </div>

          <div v-else-if="appointmentRecord" class="space-y-4 text-xs">
            <div class="bg-emerald-50/70 p-4 rounded-xl border border-emerald-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span class="text-2xs uppercase font-bold text-emerald-800">Diagnóstico Registrado:</span>
                <div class="text-sm font-bold text-emerald-950 mt-0.5">{{ appointmentRecord.diagnosis }}</div>
                <div v-if="appointmentRecord.icd10_code" class="text-2xs text-emerald-700 mt-0.5">
                  CIE-10: <span class="font-mono font-bold">{{ appointmentRecord.icd10_code }}</span> - {{ appointmentRecord.icd10_description }}
                </div>
              </div>
              <div class="text-2xs text-slate-500">
                Atendido por: <strong class="text-slate-700">{{ appointmentRecord.doctor_name }}</strong>
                <div v-if="appointmentRecord.doctor_specialty">({{ appointmentRecord.doctor_specialty }})</div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1">
                <span class="font-bold text-slate-700 flex items-center">
                  <q-icon name="notes" size="16px" class="mr-1 text-teal-600" />
                  Anamnesis y Evolución
                </span>
                <p class="text-slate-700 whitespace-pre-line leading-relaxed">{{ appointmentRecord.anamnesis }}</p>
              </div>

              <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1">
                <span class="font-bold text-slate-700 flex items-center">
                  <q-icon name="assignment" size="16px" class="mr-1 text-teal-600" />
                  Conducta Médica e Indicaciones
                </span>
                <p class="text-slate-700 whitespace-pre-line leading-relaxed">{{ appointmentRecord.plan }}</p>
              </div>
            </div>

            <div v-if="appointmentRecord.physical_exam" class="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1">
              <span class="font-bold text-slate-700 flex items-center">
                <q-icon name="monitor_heart" size="16px" class="mr-1 text-teal-600" />
                Examen Físico
              </span>
              <p class="text-slate-700">{{ appointmentRecord.physical_exam }}</p>
            </div>

            <div v-if="appointmentRecord.prescriptions?.length" class="p-4 bg-teal-50/50 rounded-xl border border-teal-200 space-y-3">
              <div class="flex items-center justify-between">
                <div class="font-bold text-slate-800 flex items-center text-xs">
                  <q-icon name="receipt_long" size="18px" class="mr-1.5 text-teal-600" />
                  Receta Médica Emitida (Folio: {{ appointmentRecord.prescriptions[0].prescription_code }})
                </div>
                <div class="flex gap-2">
                  <q-btn
                    color="teal"
                    icon="picture_as_pdf"
                    label="Descargar PDF"
                    dense
                    no-caps
                    class="text-xs px-2.5 py-1 font-bold shadow-xs"
                    @click="downloadPdf(appointmentRecord.prescriptions[0].id)"
                  />
                  <q-btn
                    outline
                    color="slate-700"
                    icon="qr_code"
                    label="QR"
                    dense
                    no-caps
                    class="text-xs px-2 py-1"
                    @click="openQrPublic(appointmentRecord.prescriptions[0].verification_hash)"
                  />
                </div>
              </div>

              <div class="space-y-1.5 divide-y divide-teal-100">
                <div v-for="(it, itIdx) in appointmentRecord.prescriptions[0].items" :key="itIdx" class="pt-1.5 flex flex-col sm:flex-row sm:items-center justify-between text-2xs">
                  <div>
                    <strong class="text-slate-800 text-xs">{{ it.medication }}</strong>
                    <span class="text-teal-700 ml-1 font-semibold">({{ it.dosage }})</span>
                    <span class="text-slate-600 ml-2">{{ it.frequency }} - {{ it.duration }}</span>
                  </div>
                  <div v-if="it.instructions" class="text-slate-500 italic">
                    {{ it.instructions }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Procedimientos Realizados (si existen) -->
            <div v-if="appointment?.procedures?.length" class="p-4 bg-teal-50/50 rounded-xl border border-teal-200 space-y-2">
              <div class="font-bold text-slate-800 flex items-center justify-between text-xs">
                <div class="flex items-center">
                  <q-icon name="healing" size="18px" class="mr-1.5 text-teal-600" />
                  Procedimientos Médicos Aplicados en Consulta ({{ appointment.procedures.length }})
                </div>
                <span class="text-xs font-black text-teal-900">
                  Total Liquidado: ${{ Number(appointment.payment_amount || 0).toFixed(2) }} {{ appointment.currency || 'USD' }}
                </span>
              </div>
              <div class="divide-y divide-teal-100/70 pt-1">
                <div
                  v-for="proc in appointment.procedures"
                  :key="proc.id"
                  class="py-1.5 flex items-center justify-between text-2xs"
                >
                  <div>
                    <span class="font-bold text-slate-800">{{ proc.name }}</span>
                    <span v-if="proc.notes" class="text-slate-500 italic ml-2">({{ proc.notes }})</span>
                  </div>
                  <span class="font-bold text-teal-800">+${{ Number(proc.price).toFixed(2) }} USD</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Formulario Activo de Consulta (Sólo si la cita no ha sido completada) -->
        <template v-if="appointment.status !== 'COMPLETED'">
          <!-- 2. Historia Clínica Estructurada (Anamnesis y Examen Físico) -->
          <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-5">
            <div class="border-b border-slate-100 pb-3 flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
                <q-icon name="edit_note" size="18px" class="mr-2 text-teal-600" />
                2. Anamnesis y Exploración Clínica (Cifrado AES-256-GCM)
              </h2>
            <div class="flex items-center text-2xs text-teal-700 bg-teal-50 py-1 px-2 rounded-lg font-medium">
              <q-icon name="lock" size="12px" class="mr-1" />
              Cifrado en Reposo por Sede
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Motivo de Consulta y Enfermedad Actual (Anamnesis) *
              </label>
              <q-input
                v-model="form.anamnesis"
                outlined
                type="textarea"
                rows="3"
                placeholder="Describir síntomas principales, tiempo de evolución, antecedentes ginecológicos (menarquía, ciclos, gestas, partos, cesáreas, abortos) y antecedentes personales."
                required
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Examen Físico y Signos Vitales (Opcional)
              </label>
              <q-input
                v-model="form.physical_exam"
                outlined
                type="textarea"
                rows="2"
                placeholder="Tensión Arterial, FC, Peso, Talla, examen mamario, abdomen, especuloscopia, tacto bimanual y hallazgos relevantes."
              />
            </div>
          </div>
        </div>

        <!-- 4. Diagnóstico CIE-10 y Conducta Médica -->
        <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-5">
          <div class="border-b border-slate-100 pb-3">
            <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
              <q-icon name="medical_services" size="18px" class="mr-2 text-teal-600" />
              3. Diagnóstico y Plan Terapéutico
            </h2>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Clasificación CIE-10 / ICD-10 Frecuente
              </label>
              <q-select
                v-model="selectedIcd10"
                :options="icd10Presets"
                option-label="label"
                outlined
                dense
                emit-value
                map-options
                placeholder="Seleccionar diagnóstico estándar..."
                @update:model-value="onIcd10Selected"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">
                Código CIE-10 Seleccionado
              </label>
              <div class="flex gap-2">
                <q-input v-model="form.icd10_code" outlined dense placeholder="Ej. Z01.4" class="w-32" />
                <q-input v-model="form.icd10_description" outlined dense placeholder="Descripción CIE-10" class="flex-1" />
              </div>
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">
              Diagnóstico Clínico Detallado *
            </label>
            <q-input
              v-model="form.diagnosis"
              outlined
              type="textarea"
              rows="2"
              placeholder="Diagnóstico presuntivo o definitivo, estadio, hallazgos de imagen."
              required
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">
              Conducta Médica y Plan de Tratamiento *
            </label>
            <q-input
              v-model="form.plan"
              outlined
              type="textarea"
              rows="3"
              placeholder="Recomendaciones higiénico-dietéticas, solicitud de paraclínicos (ecografía transvaginal, citología, mamografía), fecha de reevaluación."
              required
            />
          </div>
        </div>

        <!-- 4. Procedimientos Médicos Especializados Realizados en Consulta -->
        <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3 flex-wrap gap-2">
            <div>
              <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
                <q-icon name="healing" size="18px" class="mr-2 text-teal-600" />
                4. Procedimientos Médicos Especializados
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">
                Procedimientos adicionales realizados en la atención. Se suman y registran automáticamente en el cobro de caja.
              </p>
            </div>
            <q-btn
              color="teal-8"
              icon="add"
              label="Agregar Procedimiento Realizado"
              no-caps
              dense
              class="text-xs px-3 py-1 font-bold shadow-xs"
              @click="openAddProcedureModal"
            />
          </div>

          <!-- Si no hay procedimientos agregados -->
          <div
            v-if="!appointment.procedures || appointment.procedures.length === 0"
            class="p-4 bg-slate-50 border border-dashed border-slate-200 rounded-xl text-center text-xs text-slate-500 space-y-1"
          >
            <div>No se han registrado procedimientos complementarios para esta cita.</div>
            <div class="text-2xs text-slate-400">
              Aplica únicamente la consulta base de <strong>${{ Number(appointment.consultation_fee || 35).toFixed(2) }} USD</strong>. Si realizaste una ecografía, citología o procedimiento especial, agrégalo arriba.
            </div>
          </div>

          <!-- Lista de procedimientos agregados -->
          <div v-else class="space-y-2.5">
            <div
              v-for="(proc, pIdx) in appointment.procedures"
              :key="proc.id || pIdx"
              class="p-3.5 bg-teal-50/50 border border-teal-200/80 rounded-xl flex items-center justify-between text-xs"
            >
              <div class="flex items-center space-x-3">
                <div class="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold">
                  <q-icon name="medical_services" size="16px" />
                </div>
                <div>
                  <div class="font-bold text-slate-900">{{ proc.name }}</div>
                  <div v-if="proc.notes" class="text-2xs text-slate-500 italic">{{ proc.notes }}</div>
                </div>
              </div>

              <div class="text-right">
                <div class="font-black text-teal-900 text-sm">
                  +${{ Number(proc.price).toFixed(2) }} {{ proc.currency || 'USD' }}
                </div>
                <div class="text-3xs font-semibold text-emerald-800 bg-emerald-100 px-1.5 py-0.5 rounded inline-block mt-0.5">
                  Liquidado en Caja
                </div>
              </div>
            </div>

            <!-- Resumen Total Consulta + Procedimientos -->
            <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs bg-slate-50 p-3 rounded-xl">
              <span class="text-slate-600 font-medium">
                Honorarios totales a cobrar en caja (Consulta Base ${{ Number(appointment.consultation_fee || 35).toFixed(2) }} + Procedimientos):
              </span>
              <span class="text-base font-black text-slate-900">
                ${{ Number(appointment.payment_amount || 0).toFixed(2) }} {{ appointment.currency || 'USD' }}
              </span>
            </div>
          </div>
        </div>

        <!-- 5. Emisión de Receta Médica con Código QR -->
        <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-200 space-y-5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center">
                <q-icon name="receipt_long" size="18px" class="mr-2 text-teal-600" />
                5. Receta Médica Digital con Código QR (SHA-256)
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">Permite a las farmacias validar la autenticidad sin acceder a datos íntimos.</p>
            </div>
            <q-toggle
              v-model="includePrescription"
              label="Emitir Receta"
              color="teal"
              left-label
              class="text-xs font-semibold text-slate-700"
            />
          </div>

          <div v-if="includePrescription" class="space-y-4">
            <!-- Recordatorio de Interacciones / Tratamientos Activos -->
            <div
              v-if="activeTreatments.length > 0"
              class="p-3.5 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div class="flex items-center space-x-2">
                <q-icon name="warning_amber" size="20px" class="text-amber-600 shrink-0" />
                <span>
                  <strong>Recordatorio Farmacológico:</strong> El paciente tiene <strong>{{ activeTreatments.length }}</strong> tratamiento(s) activo(s). Verifique que los medicamentos a recetar no interactúen de forma adversa con ellos.
                </span>
              </div>
              <q-btn
                flat
                dense
                color="amber-10"
                icon="visibility"
                label="Ver activos"
                no-caps
                class="font-bold text-2xs self-start sm:self-auto shrink-0"
                @click="showHistoryDialog = true"
              />
            </div>

            <div class="space-y-3">
              <div
                v-for="(item, idx) in prescriptionItems"
                :key="idx"
                class="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 relative"
              >
                <div class="flex items-center justify-between">
                  <span class="text-xs font-bold text-teal-700">Fármaco #{{ idx + 1 }}</span>
                  <q-btn
                    v-if="prescriptionItems.length > 1"
                    flat
                    round
                    dense
                    color="negative"
                    icon="delete"
                    size="sm"
                    @click="removeItem(idx)"
                  />
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Medicamento / Principio Activo *</label>
                    <q-input v-model="item.medication" outlined dense placeholder="Ej. Ibuprofeno, Progesterona" required />
                  </div>
                  <div>
                    <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Dosis / Concentración *</label>
                    <q-input v-model="item.dosage" outlined dense placeholder="Ej. 600 mg, 100 mcg" required />
                  </div>
                  <div>
                    <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Frecuencia *</label>
                    <q-input v-model="item.frequency" outlined dense placeholder="Ej. Cada 8 horas, Diario" required />
                  </div>
                  <div>
                    <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Duración *</label>
                    <q-input v-model="item.duration" outlined dense placeholder="Ej. 5 días, 1 mes" required />
                  </div>
                </div>

                <div>
                  <label class="block text-2xs font-semibold text-slate-600 mb-0.5">Indicaciones Específicas / Vía</label>
                  <q-input v-model="item.instructions" outlined dense placeholder="Ej. Vía oral después del desayuno" />
                </div>
              </div>

              <div class="flex justify-start">
                <q-btn
                  outline
                  color="teal"
                  icon="add"
                  label="Agregar Otro Medicamento"
                  no-caps
                  dense
                  class="text-xs font-semibold px-3 py-1"
                  @click="addItem"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div>
                <label class="block text-xs font-bold text-slate-700 mb-1">Vigencia de la Receta</label>
                <q-select
                  v-model="prescriptionDurationDays"
                  :options="[
                    { label: '30 Días (Estándar)', value: 30 },
                    { label: '60 Días', value: 60 },
                    { label: '90 Días (Tratamiento Prolongado)', value: 90 },
                    { label: '15 Días', value: 15 }
                  ]"
                  option-label="label"
                  option-value="value"
                  emit-value
                  map-options
                  outlined
                  dense
                />
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-700 mb-1">Notas Generales de la Receta</label>
                <q-input
                  v-model="prescriptionNotes"
                  outlined
                  dense
                  placeholder="Ej. Mantener hidratación adecuada. Tomar con abundante agua."
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Botón de Confirmación y Cierre de Consulta -->
        <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200">
          <div class="text-xs text-slate-500 flex items-center">
            <q-icon name="security" size="18px" class="mr-1.5 text-teal-600" />
            Al guardar, la cita pasa a estado <b>COMPLETED</b> y se genera el registro inmutable de auditoría.
          </div>

          <div class="flex items-center space-x-3 w-full sm:w-auto">
            <q-btn
              flat
              color="slate-600"
              label="Cancelar"
              no-caps
              to="/appointments/my-list"
              class="w-full sm:w-auto"
            />
            <q-btn
              color="primary"
              icon="check_circle"
              label="Finalizar y Firmar Consulta"
              no-caps
              type="submit"
              class="w-full sm:w-auto font-bold px-6 py-2.5 shadow-md"
              :loading="submitting"
            />
          </div>
        </div>
      </template>

      <!-- Botón de Retorno si la Cita ya fue Completada -->
      <div v-else class="flex justify-end pt-2">
        <q-btn
          color="primary"
          icon="arrow_back"
          label="Volver a la Lista de Citas"
          no-caps
          class="font-bold px-6 py-2.5 shadow-sm text-xs"
          to="/appointments/my-list"
        />
      </div>
      </form>
    </div>

    <!-- Modal de Éxito con Descarga de Receta -->
    <q-dialog v-model="showSuccessModal" persistent>
      <q-card style="min-width: 420px; border-radius: 18px;" class="p-2">
        <q-card-section class="text-center pt-6 pb-2">
          <div class="w-16 h-16 rounded-full bg-teal-50 text-teal-600 mx-auto flex items-center justify-center mb-3">
            <q-icon name="verified" size="36px" />
          </div>
          <h3 class="text-lg font-bold text-slate-900">¡Consulta Finalizada Exitosamente!</h3>
          <p class="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            La historia médica fue cifrada con AES-256-GCM y guardada en el expediente electrónico.
          </p>
        </q-card-section>

        <q-card-section v-if="createdRecord?.prescriptions?.length" class="p-4 bg-slate-50 rounded-xl m-4 border border-slate-200 text-center space-y-3">
          <div class="text-xs font-bold text-slate-800">Receta Médica Oficial Generada</div>
          <div class="text-2xs text-slate-500">
            Folio: <span class="font-mono font-bold text-teal-700">{{ createdRecord.prescriptions[0].prescription_code }}</span>
          </div>

          <div class="flex justify-center gap-2 pt-1">
            <q-btn
              color="teal"
              icon="picture_as_pdf"
              label="Descargar Receta PDF"
              no-caps
              dense
              class="text-xs px-3 py-1.5 font-bold shadow-sm"
              @click="downloadPdf(createdRecord.prescriptions[0].id)"
            />
            <q-btn
              outline
              color="slate-700"
              icon="qr_code"
              label="Ver QR Público"
              no-caps
              dense
              class="text-xs px-3 py-1.5 font-semibold"
              @click="openQrPublic(createdRecord.prescriptions[0].verification_hash)"
            />
          </div>
        </q-card-section>

        <q-card-actions align="center" class="pb-6">
          <q-btn
            color="primary"
            label="Volver a la Lista de Citas"
            no-caps
            class="px-6 font-bold"
            to="/appointments/my-list"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Dialog / Modal de Historial Clínico Completo y Farmacovigilancia -->
    <q-dialog v-model="showHistoryDialog" position="right" maximized>
      <q-card style="width: 740px; max-width: 95vw;" class="flex flex-col h-full bg-slate-50">
        <!-- Barra de Título del Dialog -->
        <div class="bg-gradient-to-r from-teal-800 to-cyan-900 text-white p-4 flex items-center justify-between shadow-xs">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
              <q-icon name="folder_shared" size="24px" class="text-teal-200" />
            </div>
            <div>
              <h3 class="text-sm font-bold leading-tight">
                Expediente Clínico: {{ appointment?.dependent_id ? (appointment.dependent_name || 'Familiar') : appointment?.patient_name }}
              </h3>
              <p class="text-2xs text-teal-100">
                <span v-if="appointment?.dependent_id">
                  Familiar Dependiente ({{ appointment.dependent_relationship || 'Dependiente' }}) • Titular: {{ appointment.patient_name }}
                </span>
                <span v-else>
                  Paciente Titular Directo
                </span>
              </p>
            </div>
          </div>
          <q-btn flat round dense icon="close" color="white" v-close-popup />
        </div>

        <!-- Banner de Aislamiento Estricto de Historia Clínica -->
        <div class="bg-teal-900 text-teal-100 px-4 py-2 text-2xs flex items-center justify-between border-b border-teal-800">
          <div class="flex items-center gap-1.5">
            <q-icon name="lock" size="14px" class="text-teal-300" />
            <span>
              <strong>Expediente Individualizado:</strong> Consultas y recetas exclusivas de
              <strong>{{ appointment?.dependent_id ? (appointment.dependent_name || 'este familiar') : appointment?.patient_name }}</strong>, separado del titular y otros dependientes.
            </span>
          </div>
        </div>

        <!-- Resumen de Antecedentes y Triage del Paciente -->
        <div v-if="appointment?.intake_data && Object.keys(appointment.intake_data).length > 0" class="bg-teal-900/10 border-b border-teal-200/60 p-3 px-4 text-xs space-y-1.5">
          <div class="flex flex-wrap items-center gap-2 text-2xs">
            <span v-if="appointment.intake_data.blood_type" class="bg-white px-2 py-0.5 rounded border border-teal-200 font-semibold text-slate-700">
              🩸 Grupo: <strong>{{ appointment.intake_data.blood_type }}</strong>
            </span>
            <span v-if="appointment.intake_data.weight_kg" class="bg-white px-2 py-0.5 rounded border border-teal-200 text-slate-700">
              Peso: <strong>{{ appointment.intake_data.weight_kg }} kg</strong>
            </span>
            <span v-if="appointment.intake_data.height_cm" class="bg-white px-2 py-0.5 rounded border border-teal-200 text-slate-700">
              Talla: <strong>{{ appointment.intake_data.height_cm }} cm</strong>
            </span>
            <span v-if="appointment.intake_data.allergies" class="bg-red-50 text-red-900 px-2 py-0.5 rounded border border-red-200 font-bold">
              ⚠️ Alergias: {{ appointment.intake_data.allergies }}
            </span>
            <span v-if="appointment.intake_data.chronic_conditions" class="bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium">
              Antecedentes: {{ appointment.intake_data.chronic_conditions }}
            </span>
          </div>
        </div>

        <!-- Tabs de Navegación del Historial -->
        <q-tabs
          v-model="activeHistoryTab"
          dense
          class="bg-white text-slate-600 border-b border-slate-200"
          active-color="teal-8"
          indicator-color="teal-8"
          align="justify"
        >
          <q-tab name="active_meds" icon="medication" no-caps class="text-xs">
            <div class="flex items-center gap-1.5">
              <span>Tratamientos Activos</span>
              <q-badge color="orange-8" rounded text-color="white" class="font-bold text-3xs">
                {{ activeTreatments.length }}
              </q-badge>
            </div>
          </q-tab>
          <q-tab name="consultations" icon="history_edu" no-caps class="text-xs">
            <div class="flex items-center gap-1.5">
              <span>Consultas Previas</span>
              <q-badge color="slate-3" rounded text-color="slate-8" class="font-bold text-3xs">
                {{ patientHistory.length }}
              </q-badge>
            </div>
          </q-tab>
        </q-tabs>

        <!-- Contenido de las Pestañas -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
          <!-- Pestaña 1: Tratamientos Activos -->
          <div v-if="activeHistoryTab === 'active_meds'" class="space-y-3">
            <div
              v-if="activeTreatments.length > 0"
              class="p-3.5 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 space-y-1.5"
            >
              <div class="flex items-center space-x-1.5 font-bold">
                <q-icon name="warning_amber" size="20px" class="text-amber-600 shrink-0" />
                <span>Alerta de Farmacovigilancia y Prevención de Choque Terapéutico</span>
              </div>
              <p class="text-2xs text-amber-900 leading-relaxed">
                El paciente cuenta con <strong>{{ activeTreatments.length }} tratamiento(s) vigente(s)</strong> prescrito(s) previamente.
                Revise la siguiente lista de principios activos para evitar antagonismos, toxicidad acumulativa o duplicidades con los nuevos medicamentos que vaya a recetar en esta cita.
              </p>
            </div>

            <div v-if="activeTreatments.length === 0" class="p-8 text-center bg-white rounded-xl border border-slate-200 space-y-2">
              <q-icon name="check_circle" size="36px" class="text-emerald-500" />
              <div class="text-xs font-bold text-slate-800">No hay tratamientos activos en curso</div>
              <p class="text-2xs text-slate-500 max-w-sm mx-auto">
                El paciente no tiene recetas vigentes registradas por otros profesionales en el sistema.
              </p>
            </div>

            <div
              v-for="(t, idx) in activeTreatments"
              :key="'dlg-act-' + idx"
              class="bg-white p-4 rounded-xl border border-amber-200 shadow-2xs space-y-2.5 hover:border-amber-400 transition"
            >
              <div class="flex items-start justify-between">
                <div class="flex items-center space-x-2.5">
                  <div class="w-9 h-9 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center shrink-0">
                    <q-icon name="medication" size="22px" />
                  </div>
                  <div>
                    <div class="font-bold text-slate-900 text-sm">{{ t.medication }}</div>
                    <div class="text-xs font-bold text-teal-700">{{ t.dosage }}</div>
                  </div>
                </div>
                <span class="text-3xs font-bold uppercase bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-md border border-emerald-200">
                  Vigente
                </span>
              </div>

              <div class="bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs text-slate-600 space-y-1">
                <div><strong>Pauta:</strong> {{ t.frequency }} <span v-if="t.duration">• Duración: {{ t.duration }}</span></div>
                <div v-if="t.instructions"><strong>Indicaciones / Vía:</strong> {{ t.instructions }}</div>
                <div class="text-slate-500 pt-1 border-t border-slate-200/60 text-2xs">
                  <strong>Prescrito por:</strong> Dr(a). {{ t.doctor_name }} <span v-if="t.doctor_specialty">({{ t.doctor_specialty }})</span>
                  <div v-if="t.clinic_name" class="text-slate-400 text-3xs">{{ t.clinic_name }}</div>
                </div>
                <div class="flex items-center justify-between text-slate-400 pt-0.5 text-3xs">
                  <span>Emisión: {{ formatDate(t.issued_at) }}</span>
                  <span v-if="t.expires_at">Vence: {{ formatDate(t.expires_at) }}</span>
                </div>
              </div>

              <div class="flex items-center justify-between pt-1">
                <span class="font-mono text-3xs text-slate-400">Receta: {{ t.prescription_code }}</span>
                <q-btn
                  flat
                  dense
                  color="teal-8"
                  icon="picture_as_pdf"
                  label="Ver Receta Completa (PDF)"
                  no-caps
                  class="text-2xs font-semibold"
                  @click="downloadPdf(t.prescription_id)"
                />
              </div>
            </div>
          </div>

          <!-- Pestaña 2: Consultas Previas -->
          <div v-else-if="activeHistoryTab === 'consultations'" class="space-y-4">
            <div v-if="patientHistory.length === 0" class="p-8 text-center bg-white rounded-xl border border-slate-200 space-y-2">
              <q-icon name="history_edu" size="36px" class="text-slate-400" />
              <div class="text-xs font-bold text-slate-700">Sin consultas previas registradas</div>
              <p class="text-2xs text-slate-500">Ésta es la primera atención médica registrada para este paciente en el sistema.</p>
            </div>

            <div
              v-for="(rec, idx) in patientHistory"
              :key="'dlg-rec-' + rec.id"
              class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-2xs space-y-3 p-4"
            >
              <!-- Cabecera de la consulta previa -->
              <div class="flex items-center justify-between border-b border-slate-100 pb-2.5 text-xs">
                <div class="flex items-center space-x-2">
                  <div class="w-7 h-7 rounded-lg bg-teal-50 text-teal-800 font-bold flex items-center justify-center text-xs">
                    #{{ patientHistory.length - idx }}
                  </div>
                  <div>
                    <div class="flex items-center gap-1.5 flex-wrap">
                      <span class="font-bold text-slate-800">{{ formatDate(rec.created_at) }}</span>
                      <span v-if="rec.clinic_name" class="text-slate-400 text-2xs">• {{ rec.clinic_name }}</span>
                      <q-badge v-if="rec.dependent_name" color="teal-8" text-color="white" class="text-3xs font-semibold py-0.5 px-1.5">
                        {{ rec.dependent_name }} ({{ rec.dependent_relationship || 'Familiar' }})
                      </q-badge>
                    </div>
                    <div class="text-2xs text-slate-500">
                      Dr(a). <strong>{{ rec.doctor_name || 'Especialista' }}</strong>
                      <span v-if="rec.doctor_specialty">({{ rec.doctor_specialty }})</span>
                    </div>
                  </div>
                </div>

                <span v-if="rec.icd10_code" class="px-2 py-0.5 rounded-md font-mono text-2xs font-bold bg-teal-50 text-teal-800 border border-teal-200">
                  CIE-10: {{ rec.icd10_code }}
                </span>
              </div>

              <!-- Diagnóstico -->
              <div class="bg-teal-50/40 p-3 rounded-lg border border-teal-100 text-xs">
                <div class="text-2xs font-bold uppercase text-teal-800">Diagnóstico Principal:</div>
                <div class="font-bold text-slate-900 mt-0.5">{{ rec.diagnosis }}</div>
                <div v-if="rec.icd10_description" class="text-2xs text-slate-600 mt-0.5">{{ rec.icd10_description }}</div>
              </div>

              <!-- Anamnesis y Plan -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-2xs">
                <div class="bg-slate-50 p-2.5 rounded-lg border border-slate-100 space-y-1">
                  <div class="font-bold text-slate-500 uppercase text-3xs flex items-center">
                    <q-icon name="notes" size="13px" class="mr-1 text-teal-600" />
                    Motivo / Anamnesis:
                  </div>
                  <div class="text-slate-700 whitespace-pre-line leading-relaxed">{{ rec.anamnesis }}</div>
                </div>
                <div class="bg-slate-50 p-2.5 rounded-lg border border-slate-100 space-y-1">
                  <div class="font-bold text-slate-500 uppercase text-3xs flex items-center">
                    <q-icon name="assignment" size="13px" class="mr-1 text-teal-600" />
                    Conducta Médica / Plan:
                  </div>
                  <div class="text-slate-700 whitespace-pre-line leading-relaxed">{{ rec.plan }}</div>
                </div>
              </div>

              <!-- Examen Físico si existe -->
              <div v-if="rec.physical_exam" class="bg-slate-50 p-2.5 rounded-lg border border-slate-100 space-y-0.5 text-2xs">
                <div class="font-bold text-slate-500 uppercase text-3xs flex items-center">
                  <q-icon name="monitor_heart" size="13px" class="mr-1 text-teal-600" />
                  Examen Físico y Signos Vitales:
                </div>
                <div class="text-slate-700">{{ rec.physical_exam }}</div>
              </div>

              <!-- Recetas asociadas y medicamentos prescritos -->
              <div v-if="rec.prescriptions?.length" class="border-t border-slate-100 pt-2 space-y-2">
                <div class="text-3xs font-bold uppercase tracking-wider text-slate-500 flex items-center">
                  <q-icon name="receipt_long" size="14px" class="mr-1 text-teal-600" />
                  Receta(s) emitida(s) en esta consulta:
                </div>

                <div v-for="p in rec.prescriptions" :key="p.id" class="p-3 bg-teal-50/40 rounded-xl border border-teal-100 space-y-2">
                  <div class="flex items-center justify-between">
                    <div>
                      <span class="font-mono font-bold text-teal-800 text-xs">{{ p.prescription_code }}</span>
                      <span class="text-3xs text-slate-400 ml-2">Emitido: {{ formatDate(p.issued_at) }}</span>
                      <span class="text-3xs font-semibold ml-2" :class="isVigente(p.expires_at) ? 'text-emerald-700' : 'text-slate-400'">
                        {{ isVigente(p.expires_at) ? '● Vigente' : '● Concluido' }}
                      </span>
                    </div>
                    <q-btn
                      flat
                      dense
                      size="sm"
                      color="teal-8"
                      icon="picture_as_pdf"
                      label="Descargar PDF"
                      no-caps
                      @click="downloadPdf(p.id)"
                    />
                  </div>

                  <!-- Lista detallada de medicamentos de esta receta -->
                  <div v-if="p.items?.length" class="divide-y divide-teal-100/60 pt-1">
                    <div v-for="(it, itIdx) in p.items" :key="itIdx" class="py-1 text-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                      <div>
                        <strong class="text-slate-800">{{ it.medication }}</strong>
                        <span class="text-teal-700 ml-1 font-semibold">({{ it.dosage }})</span>
                        <span class="text-slate-600 ml-2">{{ it.frequency }} - {{ it.duration }}</span>
                      </div>
                      <div v-if="it.instructions" class="text-slate-500 italic">
                        {{ it.instructions }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </q-card>
    </q-dialog>

    <!-- Modal para Agregar Procedimiento Intra-Consulta -->
    <q-dialog v-model="showAddProcModal">
      <q-card style="min-width: 440px; max-width: 520px; border-radius: 16px;">
        <q-card-section class="bg-teal-700 text-white p-4 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <q-icon name="healing" size="22px" />
            <h3 class="font-bold text-sm">Registrar Procedimiento Realizado</h3>
          </div>
          <q-btn flat round dense icon="close" text-color="white" v-close-popup />
        </q-card-section>

        <q-card-section class="p-5 space-y-4">
          <div class="p-3 bg-teal-50 border border-teal-200 rounded-xl text-xs text-teal-900 space-y-1">
            <div class="font-bold flex items-center gap-1.5">
              <q-icon name="point_of_sale" size="16px" color="teal" />
              Impacto Inmediato en Arqueo de Caja:
            </div>
            <p class="text-2xs text-teal-800 m-0 leading-relaxed">
              Al agregar este procedimiento, el importe a liquidar del paciente en caja se actualizará automáticamente con el desglose correspondiente.
            </p>
          </div>

          <!-- Selector del Catálogo si existe -->
          <div v-if="availableProcedures.length > 0">
            <label class="block text-xs font-bold text-slate-700 mb-1">Elegir del Catálogo de la Sede</label>
            <q-select
              v-model="selectedCatalogProc"
              :options="availableProcedures"
              option-label="label"
              outlined
              dense
              clearable
              placeholder="Seleccionar procedimiento..."
              @update:model-value="onSelectCatalogProc"
            />
          </div>

          <div class="space-y-3 pt-1">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Nombre del Procedimiento *</label>
              <q-input
                v-model="newProcForm.name"
                outlined
                dense
                placeholder="Ej. Ecografía Pélvica / Citología Especializada"
                required
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Monto a Facturar en Caja (USD) *</label>
              <q-input
                v-model.number="newProcForm.price"
                type="number"
                step="0.01"
                min="0"
                outlined
                dense
                prefix="$"
                suffix="USD"
                required
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Observaciones / Hallazgo Rápido (Opcional)</label>
              <q-input
                v-model="newProcForm.notes"
                outlined
                dense
                placeholder="Ej. Realizado con transductor endocavitario, sin dolor."
              />
            </div>
          </div>

          <div class="flex justify-end space-x-2 pt-3 border-t border-slate-100">
            <q-btn flat label="Cancelar" no-caps v-close-popup />
            <q-btn
              color="teal-8"
              icon="add_circle"
              label="Agregar y Cargar a Caja"
              no-caps
              class="font-semibold"
              :loading="savingProcedure"
              @click="submitAddProcedure"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from 'boot/axios'
import { Notify } from 'quasar'

const route = useRoute()
const router = useRouter()

const appointmentId = ref(route.query.appointment_id || '')
const appointment = ref(null)
const loadingAppointment = ref(true)
const submitting = ref(false)
const showSuccessModal = ref(false)
const createdRecord = ref(null)

// Procedimientos y servicios en consulta
const showAddProcModal = ref(false)
const availableProcedures = ref([])
const selectedCatalogProc = ref(null)
const savingProcedure = ref(false)
const newProcForm = reactive({
  procedure_id: null,
  name: '',
  price: 0,
  currency: 'USD',
  notes: ''
})

// Estados de Historial Clínico y Farmacovigilancia
const patientHistory = ref([])
const loadingHistory = ref(false)
const activeTreatments = ref([])
const showHistoryDialog = ref(false)
const activeHistoryTab = ref('active_meds')

// Estado si la consulta ya fue completada previamente
const appointmentRecord = ref(null)
const loadingAppointmentRecord = ref(false)

const includePrescription = ref(true)
const prescriptionDurationDays = ref(30)
const prescriptionNotes = ref('')

const form = ref({
  anamnesis: '',
  physical_exam: '',
  diagnosis: '',
  plan: '',
  icd10_code: '',
  icd10_description: ''
})

const prescriptionItems = ref([
  {
    medication: '',
    dosage: '',
    frequency: '',
    duration: '',
    instructions: ''
  }
])

const icd10Presets = [
  { label: 'Z01.4 - Examen ginecológico general de rutina', code: 'Z01.4', desc: 'Examen ginecológico general' },
  { label: 'N94.4 - Dismenorrea primaria', code: 'N94.4', desc: 'Dismenorrea primaria' },
  { label: 'N94.6 - Dismenorrea no especificada', code: 'N94.6', desc: 'Dismenorrea no especificada' },
  { label: 'N92.0 - Menorragia o menstruación excesiva', code: 'N92.0', desc: 'Menstruación excesiva y frecuente' },
  { label: 'N76.0 - Vaginitis aguda', code: 'N76.0', desc: 'Vaginitis aguda' },
  { label: 'N80.0 - Endometriosis del útero', code: 'N80.0', desc: 'Endometriosis del útero' },
  { label: 'Z34.0 - Supervisión de primer embarazo normal', code: 'Z34.0', desc: 'Supervisión de primer embarazo normal' },
  { label: 'N95.1 - Síntomas menopáusicos y climatéricos', code: 'N95.1', desc: 'Estados menopáusicos y climatéricos' },
  { label: 'Z30.0 - Asesoramiento sobre anticoncepción', code: 'Z30.0', desc: 'Consejo y asesoramiento general sobre la anticoncepción' },
  { label: 'R10.2 - Dolor pélvico y perineal', code: 'R10.2', desc: 'Dolor pélvico y perineal' }
]

const selectedIcd10 = ref(null)

function onIcd10Selected (preset) {
  if (!preset) return
  form.value.icd10_code = preset.code
  form.value.icd10_description = preset.desc
  if (!form.value.diagnosis) {
    form.value.diagnosis = preset.desc
  }
}

function addItem () {
  prescriptionItems.value.push({
    medication: '',
    dosage: '',
    frequency: '',
    duration: '',
    instructions: ''
  })
}

function removeItem (index) {
  if (prescriptionItems.value.length > 1) {
    prescriptionItems.value.splice(index, 1)
  }
}

function formatDateTime (iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDate (iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

function isVigente (expiresAt) {
  if (!expiresAt) return true
  return new Date(expiresAt) >= new Date()
}

function computeTreatments () {
  const now = new Date()
  const active = []
  for (const rec of patientHistory.value) {
    if (!rec.prescriptions || !Array.isArray(rec.prescriptions)) continue
    for (const presc of rec.prescriptions) {
      const isPrescActive = presc.status === 'ACTIVE' && (!presc.expires_at || new Date(presc.expires_at) >= now)
      if (isPrescActive && presc.items && Array.isArray(presc.items)) {
        for (const item of presc.items) {
          active.push({
            medication: item.medication,
            dosage: item.dosage,
            frequency: item.frequency,
            duration: item.duration,
            instructions: item.instructions,
            route: item.route,
            doctor_name: rec.doctor_name || 'Especialista',
            doctor_specialty: rec.doctor_specialty || '',
            clinic_name: rec.clinic_name || 'Clínica ÍntimaSalud',
            issued_at: presc.issued_at,
            expires_at: presc.expires_at,
            prescription_code: presc.prescription_code,
            prescription_id: presc.id,
            diagnosis_summary: presc.diagnosis_summary || rec.diagnosis
          })
        }
      }
    }
  }
  activeTreatments.value = active
}

async function fetchPatientHistory (patientId, dependentId) {
  if (!patientId) return
  loadingHistory.value = true
  try {
    const params = {}
    if (dependentId) params.dependent_id = dependentId
    const { data } = await api.get(`/medical-records/patient/${patientId}`, { params })
    const allRecords = Array.isArray(data) ? data : []
    // Excluir la cita actual si ya fue completada para que "Consultas Previas" sean estrictamente anteriores
    patientHistory.value = allRecords.filter(r => r.appointment_id !== appointmentId.value)
    computeTreatments()
  } catch (err) {
    console.error('Error al cargar historial del paciente:', err)
  } finally {
    loadingHistory.value = false
  }
}

async function fetchAppointmentRecord (apptId) {
  if (!apptId) return
  loadingAppointmentRecord.value = true
  try {
    const { data } = await api.get(`/medical-records/appointment/${apptId}`)
    appointmentRecord.value = data
  } catch (err) {
    // Si aún no está creada la historia para esta cita, no es error bloqueante
    appointmentRecord.value = null
  } finally {
    loadingAppointmentRecord.value = false
  }
}

async function fetchAppointment () {
  if (!appointmentId.value) {
    loadingAppointment.value = false
    return
  }
  loadingAppointment.value = true
  try {
    let match = null
    try {
      const resSingle = await api.get(`/appointments/${appointmentId.value}`)
      match = resSingle.data
    } catch {
      const { data } = await api.get('/appointments')
      match = data.find(a => a.id === appointmentId.value)
    }
    if (match) {
      appointment.value = match
      if (match.patient_id) {
        fetchPatientHistory(match.patient_id, match.dependent_id)
      }
      if (match.status === 'COMPLETED') {
        fetchAppointmentRecord(match.id)
      }
      if (match.clinic_id) {
        fetchAvailableProcedures(match.clinic_id, match.doctor_id)
      }
    } else {
      Notify.create({ type: 'warning', message: 'No se encontró la cita especificada.' })
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al consultar datos de la cita.' })
  } finally {
    loadingAppointment.value = false
  }
}

async function submitConsultation () {
  submitting.value = true
  try {
    const payload = {
      appointment_id: appointmentId.value,
      anamnesis: form.value.anamnesis,
      physical_exam: form.value.physical_exam || undefined,
      diagnosis: form.value.diagnosis,
      plan: form.value.plan,
      icd10_code: form.value.icd10_code || undefined,
      icd10_description: form.value.icd10_description || undefined
    }

    if (includePrescription.value) {
      const validItems = prescriptionItems.value.filter(i => i.medication && i.dosage)
      if (validItems.length === 0) {
        Notify.create({ type: 'warning', message: 'Indica al menos un medicamento en la receta o desactiva la opción.' })
        submitting.value = false
        return
      }

      payload.prescription = {
        items: validItems,
        diagnosis_summary: form.value.icd10_description || form.value.diagnosis,
        notes: prescriptionNotes.value || undefined,
        duration_days: prescriptionDurationDays.value
      }
    }

    const { data } = await api.post('/medical-records', payload)
    createdRecord.value = data
    showSuccessModal.value = true
    Notify.create({
      type: 'positive',
      message: 'Consulta médica registrada y firmada con éxito.'
    })
  } catch (err) {
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'Error al registrar historia clínica.'
    })
  } finally {
    submitting.value = false
  }
}

async function downloadPdf (prescriptionId) {
  try {
    const resp = await api.get(`/medical-records/prescriptions/${prescriptionId}/pdf`, {
      responseType: 'blob'
    })
    const blob = new Blob([resp.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Receta_${prescriptionId.slice(0, 8)}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (err) {
    Notify.create({ type: 'negative', message: 'Error al descargar PDF de receta.' })
  }
}

function openQrPublic (hash) {
  const routeData = router.resolve({ path: `/verify-prescription/${hash}` })
  window.open(routeData.href, '_blank')
}

async function fetchAvailableProcedures (clinicId, doctorId) {
  if (!clinicId) return
  try {
    const params = {}
    if (doctorId) params.doctor_id = doctorId
    const res = await api.get(`/clinics/${clinicId}/procedures`, { params })
    availableProcedures.value = (res.data || []).map(p => ({
      ...p,
      label: `${p.name} - $${Number(p.price).toFixed(2)} USD`
    }))
  } catch (err) {
    console.error('Error cargando catálogo de procedimientos:', err)
  }
}

function openAddProcedureModal () {
  selectedCatalogProc.value = null
  newProcForm.procedure_id = null
  newProcForm.name = ''
  newProcForm.price = 0
  newProcForm.currency = 'USD'
  newProcForm.notes = ''
  showAddProcModal.value = true
}

function onSelectCatalogProc (proc) {
  if (!proc) {
    newProcForm.procedure_id = null
    return
  }
  newProcForm.procedure_id = proc.id
  newProcForm.name = proc.name
  newProcForm.price = Number(proc.price)
  newProcForm.currency = proc.currency || 'USD'
}

async function submitAddProcedure () {
  if (!newProcForm.name || newProcForm.price == null || Number(newProcForm.price) < 0) {
    Notify.create({ type: 'warning', message: 'Indica el nombre y un precio válido para el procedimiento.' })
    return
  }
  savingProcedure.value = true
  try {
    const payload = {
      procedure_id: newProcForm.procedure_id || null,
      name: newProcForm.name,
      price: Number(newProcForm.price),
      currency: newProcForm.currency || 'USD',
      notes: newProcForm.notes || null
    }
    const res = await api.post(`/appointments/${appointment.value.id}/procedures`, payload)
    appointment.value = res.data
    Notify.create({
      type: 'positive',
      message: `Procedimiento "${newProcForm.name}" agregado exitosamente. Monto en caja actualizado.`,
      icon: 'verified'
    })
    showAddProcModal.value = false
  } catch (err) {
    console.error('Error al agregar procedimiento:', err)
    Notify.create({
      type: 'negative',
      message: err.response?.data?.detail || 'No se pudo registrar el procedimiento.'
    })
  } finally {
    savingProcedure.value = false
  }
}

onMounted(() => {
  fetchAppointment()
})
</script>
