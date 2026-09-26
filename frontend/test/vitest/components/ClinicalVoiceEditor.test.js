import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ClinicalVoiceEditor from 'src/components/medical/ClinicalVoiceEditor.vue'
import { api } from 'src/boot/axios'

vi.mock('src/boot/axios', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn()
  }
}))

const mockNotify = vi.fn()
vi.mock('quasar', () => ({
  useQuasar: () => ({
    notify: mockNotify
  })
}))

describe('ClinicalVoiceEditor.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renderiza etiqueta requerida y contenido inicial correctamente', () => {
    const wrapper = mount(ClinicalVoiceEditor, {
      props: {
        modelValue: '<p>Dolor en fosa ilíaca derecha</p>',
        label: 'Motivo de Consulta y Enfermedad Actual (Anamnesis)',
        required: true,
        clinicId: 'clinic-123',
        aiEnabled: false
      },
      global: {
        stubs: {
          'q-editor': {
            template: '<div class="q-editor-stub"><slot /></div>',
            props: ['modelValue']
          },
          'q-btn': {
            template: '<button class="q-btn-stub" @click="$emit(\'click\')">{{ label }}<slot /></button>',
            props: ['label']
          },
          'q-tooltip': true,
          'q-badge': {
            template: '<span class="q-badge-stub"><slot /></span>'
          },
          'q-icon': true,
          'q-dialog': true,
          'q-card': true,
          'q-card-section': true,
          'q-card-actions': true,
          'q-input': true
        }
      }
    })

    expect(wrapper.text()).toContain('Motivo de Consulta y Enfermedad Actual (Anamnesis)')
    expect(wrapper.text()).toContain('*')
    expect(wrapper.text()).toContain('Dictar')
    expect(wrapper.text()).toContain('IA no habilitada en sede')
  })

  it('muestra el botón Mejorar con IA cuando aiEnabled es true', () => {
    const wrapper = mount(ClinicalVoiceEditor, {
      props: {
        modelValue: 'Paciente femenina de 32 años',
        label: 'Diagnóstico Clínico Detallado',
        required: true,
        clinicId: 'clinic-123',
        aiEnabled: true
      },
      global: {
        stubs: {
          'q-editor': true,
          'q-btn': {
            template: '<button class="q-btn-stub" @click="$emit(\'click\')">{{ label }}<slot /></button>',
            props: ['label']
          },
          'q-tooltip': true,
          'q-badge': true,
          'q-icon': true,
          'q-dialog': true,
          'q-card': true,
          'q-card-section': true,
          'q-card-actions': true,
          'q-input': true
        }
      }
    })

    expect(wrapper.text()).toContain('Mejorar con IA')
    expect(wrapper.text()).not.toContain('IA no habilitada en sede')
  })

  it('advierte al usuario si intenta usar IA con un campo vacío', async () => {
    const wrapper = mount(ClinicalVoiceEditor, {
      props: {
        modelValue: '',
        label: 'Conducta Médica',
        required: true,
        clinicId: 'clinic-123',
        aiEnabled: true
      },
      global: {
        stubs: {
          'q-editor': true,
          'q-btn': true,
          'q-tooltip': true,
          'q-badge': true,
          'q-icon': true,
          'q-dialog': true,
          'q-card': true,
          'q-card-section': true,
          'q-card-actions': true,
          'q-input': true
        }
      }
    })

    await wrapper.vm.requestAiEnhancement()
    expect(mockNotify).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'warning',
        message: expect.stringContaining('Dicta o redacta información en este campo')
      })
    )
    expect(api.post).not.toHaveBeenCalled()
  })

  it('llama al endpoint /medical-records/ai-assist cuando el texto es válido', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        enhanced_text: 'Paciente femenina acude refiriendo dolor pélvico recurrente.',
        provider: 'external_ai_gateway'
      }
    })

    const wrapper = mount(ClinicalVoiceEditor, {
      props: {
        modelValue: '<p>paciente con dolor pelvico</p>',
        label: 'Anamnesis',
        fieldType: 'anamnesis',
        clinicId: 'clinic-xyz-789',
        aiEnabled: true
      },
      global: {
        stubs: {
          'q-editor': true,
          'q-btn': true,
          'q-tooltip': true,
          'q-badge': true,
          'q-icon': true,
          'q-dialog': true,
          'q-card': true,
          'q-card-section': true,
          'q-card-actions': true,
          'q-input': true
        }
      }
    })

    await wrapper.vm.requestAiEnhancement()
    expect(api.post).toHaveBeenCalledWith(
      '/medical-records/ai-assist',
      expect.objectContaining({
        clinic_id: 'clinic-xyz-789',
        field_type: 'anamnesis',
        tone: 'formal_clinical'
      }),
      expect.any(Object)
    )
    expect(wrapper.vm.showAiReviewModal).toBe(true)
    expect(wrapper.vm.aiEnhancedDraft).toBe('Paciente femenina acude refiriendo dolor pélvico recurrente.')
  })
})
