import { describe, it, expect } from 'vitest'
import { unifyDepartmentOptions, type DepartmentOption } from '../utils/departments'

describe('unifyDepartmentOptions', () => {
  const defaults: DepartmentOption[] = [
    { label: 'Out Patient Department', value: 'OPD' },
    { label: 'Pharmacy', value: 'Pharmacy' },
    { label: 'Appointment', value: 'Appointment' },
  ]

  it('merges unique backend string values', () => {
    const backend = ['Cardiology', 'Dermatology']
    const union = unifyDepartmentOptions(defaults, backend)
    const values = union.map(d => d.value)
    expect(values).toContain('OPD')
    expect(values).toContain('Cardiology')
    expect(values).toContain('Dermatology')
  })

  it('preserves provided labels and values from backend objects', () => {
    const backend = [
      { label: 'General Medicine', value: 'general-medicine' },
      { label: 'Emergency Medicine', value: 'emergency-medicine' },
    ]
    const union = unifyDepartmentOptions(defaults, backend)
    const gm = union.find(d => d.value === 'general-medicine')
    const em = union.find(d => d.value === 'emergency-medicine')
    expect(gm?.label).toBe('General Medicine')
    expect(em?.label).toBe('Emergency Medicine')
  })

  it('avoids duplicates by value', () => {
    const backend = [{ label: 'Pharmacy', value: 'Pharmacy' }]
    const union = unifyDepartmentOptions(defaults, backend)
    const pharmacies = union.filter(d => d.value === 'Pharmacy')
    expect(pharmacies.length).toBe(1)
  })

  it('falls back to defaults when backend empty', () => {
    const union = unifyDepartmentOptions(defaults, [])
    expect(union).toEqual(defaults)
  })
})

