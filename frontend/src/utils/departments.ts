export type DepartmentOption = { label: string; value: string };

// Shared list used across PatientAppointment and Doctor settings/registration
export const departmentOptions: DepartmentOption[] = [
  { label: 'General Medicine', value: 'general-medicine' },
  { label: 'Cardiology', value: 'cardiology' },
  { label: 'Dermatology', value: 'dermatology' },
  { label: 'Orthopedics', value: 'orthopedics' },
  { label: 'Pediatrics', value: 'pediatrics' },
  { label: 'Gynecology', value: 'gynecology' },
  { label: 'Neurology', value: 'neurology' },
  { label: 'Oncology', value: 'oncology' },
  { label: 'Optometrist', value: 'optometrist' },
  { label: 'Emergency Medicine', value: 'emergency-medicine' },
  // Fallback to avoid breaking when existing values don’t match known departments
  { label: 'Other', value: 'other' },
];

/**
 * Build a unified department options list by merging local queue defaults
 * with backend-provided departments. Handles both string and object formats
 * from the API and preserves labels when available. Duplicates are removed
 * by department value.
 */
export function unifyDepartmentOptions(
  queueDefaults: DepartmentOption[],
  rawBackend: Array<string | { value?: string; label?: string }>
): DepartmentOption[] {
  const backendOptions: DepartmentOption[] = rawBackend
    .map((item) => {
      if (typeof item === 'string') return { label: item, value: item };
      if (item && typeof item === 'object') {
        const value = typeof item.value === 'string' ? item.value : (typeof item.label === 'string' ? item.label : '');
        const label = typeof item.label === 'string' ? item.label : value;
        if (value) return { label, value };
      }
      return null;
    })
    .filter((opt): opt is DepartmentOption => !!opt);

  const existing = new Set(queueDefaults.map((d) => d.value));
  const union: DepartmentOption[] = [...queueDefaults];
  backendOptions.forEach((opt) => {
    if (!existing.has(opt.value)) {
      union.push(opt);
      existing.add(opt.value);
    }
  });
  return union.length ? union : queueDefaults;
}
