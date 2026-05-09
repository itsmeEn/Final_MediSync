export type AssessmentUser = { id: number; role?: string }

export type AssessmentPatient = {
  source?: string
  appointment_id?: number
  appointment_status?: string
  assignment_id?: number
  assigned_doctor_id?: number
}

export function canAssessPatientForUser(user: AssessmentUser, patient: AssessmentPatient): boolean {
  const userId = Number(user?.id ?? NaN)
  if (!Number.isFinite(userId) || userId <= 0) return false

  const source = String(patient?.source ?? '').trim().toLowerCase()
  const assignmentId = Number(patient?.assignment_id ?? NaN)
  if (source === 'queue' || (Number.isFinite(assignmentId) && assignmentId > 0)) return false

  const apptId = Number(patient?.appointment_id ?? NaN)
  if (!Number.isFinite(apptId) || apptId <= 0) return false

  const status = String(patient?.appointment_status ?? '').trim().toLowerCase()
  if (status && !['scheduled', 'rescheduled', 'in_progress'].includes(status)) return false

  const assignedDoctorId = Number(patient?.assigned_doctor_id ?? NaN)
  if (!Number.isFinite(assignedDoctorId) || assignedDoctorId <= 0) return false

  return assignedDoctorId === userId
}

