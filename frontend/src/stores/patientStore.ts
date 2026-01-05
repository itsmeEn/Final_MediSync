import { defineStore } from 'pinia';
import { ref } from 'vue';

export interface Patient {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  age: number | null;
  gender: string;
  blood_type: string;
  medical_condition: string;
  hospital: string;
  insurance_provider: string;
  billing_amount: number | null;
  room_number: string;
  admission_type: string;
  date_of_admission: string | null;
  discharge_date: string | null;
  medication: string;
  test_results: string;
  assigned_doctor: string | null;
  profile_picture?: string | null;
  is_dummy?: boolean;
}

export const usePatientStore = defineStore('patient', () => {
  const currentPatient = ref<Patient | null>(null);

  const setCurrentPatient = (data: Record<string, unknown> | null | undefined) => {
    try {
      if (!data) {
        currentPatient.value = null;
        localStorage.removeItem('current_serving_patient');
        return;
      }

      // Normalize data to Patient type
      const normalized: Patient = {
        id: Number(data.id ?? data.user_id ?? 0),
        user_id: Number(data.user_id ?? data.id ?? 0),
        full_name: typeof data.full_name === 'string' ? data.full_name : (typeof data.name === 'string' ? data.name : ''),
        email: typeof data.email === 'string' ? data.email : '',
        age: typeof data.age === 'number' ? data.age : null,
        gender: typeof data.gender === 'string' ? data.gender : '',
        blood_type: typeof data.blood_type === 'string' ? data.blood_type : '',
        medical_condition: typeof data.medical_condition === 'string' ? data.medical_condition : '',
        hospital: typeof data.hospital === 'string' ? data.hospital : '',
        insurance_provider: typeof data.insurance_provider === 'string' ? data.insurance_provider : '',
        billing_amount: typeof data.billing_amount === 'number' ? data.billing_amount : null,
        room_number: typeof data.room_number === 'string' ? data.room_number : '',
        admission_type: typeof data.admission_type === 'string' ? data.admission_type : '',
        date_of_admission: typeof data.date_of_admission === 'string' ? data.date_of_admission : null,
        discharge_date: typeof data.discharge_date === 'string' ? data.discharge_date : null,
        medication: typeof data.medication === 'string' ? data.medication : '',
        test_results: typeof data.test_results === 'string' ? data.test_results : '',
        assigned_doctor: typeof data.assigned_doctor === 'string' ? data.assigned_doctor : null,
        profile_picture: typeof data.profile_picture === 'string' ? data.profile_picture : null,
        is_dummy: false
      };

      currentPatient.value = normalized;
      localStorage.setItem('current_serving_patient', JSON.stringify(normalized));
    } catch (error) {
      console.error('Failed to set current patient:', error);
      throw error;
    }
  };

  const loadFromStorage = () => {
    try {
      const raw = localStorage.getItem('current_serving_patient');
      if (raw) {
        currentPatient.value = JSON.parse(raw);
      }
    } catch (error) {
      console.warn('Failed to load patient from storage', error);
      localStorage.removeItem('current_serving_patient');
    }
  };

  const clearCurrentPatient = () => {
    currentPatient.value = null;
    localStorage.removeItem('current_serving_patient');
  };

  return {
    currentPatient,
    setCurrentPatient,
    loadFromStorage,
    clearCurrentPatient
  };
});
