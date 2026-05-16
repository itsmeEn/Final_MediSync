import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RiskAssessmentCard from 'src/components/analytics/RiskAssessmentCard.vue'

const stubs = {
  'q-card': { template: '<div><slot /></div>' },
  'q-card-section': { template: '<div><slot /></div>' },
  'q-icon': { template: '<i />' },
  'q-chip': { template: '<span><slot /></span>' },
  'q-tooltip': { template: '<span><slot /></span>' },
  'q-expansion-item': { props: ['label'], template: '<section><div>{{ label }}</div><div><slot /></div></section>' },
}

describe('RiskAssessmentCard.vue', () => {
  it('renders numeric and qualitative confidence in header', () => {
    const wrapper = mount(RiskAssessmentCard, {
      props: {
        risk: {
          overall_risk: 'moderate',
          risk_score: 63.2,
          confidence: 78.4,
          confidence_label: 'Medium',
          chi_square: 8.342,
          p_value: 0.0502,
          recommended_actions: [{ text: 'Follow-up within 24–48 hours', priority: 'High' }],
          risks: [{ title: 'Test risk', confidence: 86.2, confidence_label: 'High', impact: 4, likelihood: 4, business_criticality: 5 }],
        },
      },
      global: { stubs },
    })

    expect(wrapper.text()).toContain('Overall risk: moderate')
    expect(wrapper.text()).toContain('Risk score: 63/100')
    expect(wrapper.text()).toContain('78.40% (Medium) confidence')
  })

  it('renders recommended actions with priority tags', () => {
    const wrapper = mount(RiskAssessmentCard, {
      props: {
        risk: {
          overall_risk: 'high',
          risk_score: 82,
          confidence: 92.5,
          confidence_label: 'High',
          recommended_actions: [
            { text: 'Do something urgent', priority: 'High', owner: 'Nurse Supervisor', success_metric: 'Done', confidence: 91, confidence_label: 'High' },
            { text: 'Review trends', priority: 'Medium' },
            { text: 'Update education materials', priority: 'Low' },
          ],
        },
      },
      global: { stubs },
    })

    expect(wrapper.text()).toContain('Recommended action')
    expect(wrapper.text()).toContain('High')
    expect(wrapper.text()).toContain('Medium')
    expect(wrapper.text()).toContain('Low')
    expect(wrapper.text()).toContain('91% High')
    expect(wrapper.text()).toContain('Do something urgent')
  })
})
