import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import AiConsultationAssistantModal from 'src/components/medical/AiConsultationAssistantModal.vue'
import { api } from 'src/boot/axios'

vi.mock('src/boot/axios', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn()
  }
}))

vi.mock('quasar', () => ({
  Notify: {
    create: vi.fn()
  }
}))

describe('AiConsultationAssistantModal.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: [] })
  })

  it('renderiza título, especialidad y controles de grabación cuando está abierto', () => {
    const wrapper = mount(AiConsultationAssistantModal, {
      props: {
        modelValue: true,
        appointmentId: 'appt-12345',
        doctorSpecialty: 'Ginecología y Obstetricia',
        clinicId: 'clinic-999'
      },
      global: {
        stubs: {
          'q-dialog': {
            template: '<div class="q-dialog-stub"><slot /></div>',
            props: ['modelValue']
          },
          'q-card': { template: '<div class="q-card-stub"><slot /></div>' },
          'q-card-section': { template: '<div class="q-card-section-stub"><slot /></div>' },
          'q-card-actions': { template: '<div class="q-card-actions-stub"><slot /></div>' },
          'q-btn': {
            template: '<button class="q-btn-stub" @click="$emit(\'click\')">{{ label }}<slot /></button>',
            props: ['label']
          },
          'q-badge': { template: '<span class="q-badge-stub"><slot /></span>' },
          'q-icon': true,
          'q-input': {
            template: '<textarea class="q-input-stub" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
            props: ['modelValue']
          },
          'q-spinner-orbit': true,
          'q-tooltip': true
        }
      }
    })

    expect(wrapper.text()).toContain('Consulta Médica Asistida por IA')
    expect(wrapper.text()).toContain('Ginecología y Obstetricia')
    expect(wrapper.text()).toContain('Iniciar Grabación de Consulta')
    expect(wrapper.text()).toContain('Tomar Foto / Subir Archivo')
  })

  it('solicita los anexos previos de la cita al montarse con modelValue=true', () => {
    mount(AiConsultationAssistantModal, {
      props: {
        modelValue: true,
        appointmentId: 'appt-abc-999',
        doctorSpecialty: 'Cardiología'
      },
      global: {
        stubs: {
          'q-dialog': { template: '<div><slot /></div>' },
          'q-card': true,
          'q-card-section': true,
          'q-card-actions': true,
          'q-btn': true,
          'q-badge': true,
          'q-icon': true,
          'q-input': true,
          'q-spinner-orbit': true,
          'q-tooltip': true
        }
      }
    })

    expect(api.get).toHaveBeenCalledWith('/appointments/appt-abc-999/attachments')
  })

  it('emite apply-prefill con los datos analizados por IA al presionar procesar', async () => {
    api.post.mockResolvedValue({
      data: {
        anamnesis: 'Paciente refiere dolor torácico opresivo de esfuerzo.',
        physical_exam: 'TA 140/90, FC 88 lpm, auscultación cardiopulmonar rítmica.',
        diagnosis: 'Angina de pecho estable.',
        icd10_code: 'I20.9',
        icd10_description: 'Angina de pecho, no especificada',
        plan: 'Reposo relativo, ECG de 12 derivaciones y ecocardiograma transtorácico.',
        prescriptions: [
          {
            medication: 'Aspirina',
            dosage: '100 mg',
            frequency: 'Cada 24 horas',
            duration: 'Uso continuo',
            instructions: 'Vía oral después del almuerzo'
          }
        ],
        clinical_summary: 'Sospecha de coronariopatía en estudio.'
      }
    })


    const wrapper = mount(AiConsultationAssistantModal, {
      props: {
        modelValue: true,
        appointmentId: 'appt-cardio-1',
        doctorSpecialty: 'Cardiología'
      },
      global: {
        stubs: {
          'q-dialog': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-btn': {
            template: '<button class="q-btn-stub" @click="$emit(\'click\')">{{ label }}<slot /></button>',
            props: ['label']
          },
          'q-badge': true,
          'q-icon': true,
          'q-input': {
            template: '<input class="q-input-stub" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
            props: ['modelValue']
          },
          'q-spinner-orbit': true,
          'q-tooltip': true
        }
      }
    })

    // Escribir texto de transcripción
    const input = wrapper.find('input.q-input-stub')
    await input.setValue('Doctor pregunta por dolor en el pecho, paciente refiere opresión al subir escaleras.')

    // Presionar botón de procesar
    const processBtn = wrapper.findAll('button.q-btn-stub').find(b => b.text().includes('Detener y Prellenar'))
    expect(processBtn).toBeDefined()
    await processBtn.trigger('click')

    expect(api.post).toHaveBeenCalledWith(
      '/medical-records/ai-consultation-assist',
      expect.objectContaining({
        appointment_id: 'appt-cardio-1',
        doctor_specialty: 'Cardiología'
      })
    )

    expect(wrapper.emitted('apply-prefill')).toBeTruthy()
    const prefillData = wrapper.emitted('apply-prefill')[0][0]
    expect(prefillData.icd10_code).toBe('I20.9')
    expect(prefillData.diagnosis).toBe('Angina de pecho estable.')
    expect(prefillData.prescriptions[0].medication).toBe('Aspirina')
  })
})
