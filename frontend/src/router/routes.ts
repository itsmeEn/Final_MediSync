import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    component: () => import('pages/LoginPage.vue'),
  },
  {
    path: '/forgot-password',
    component: () => import('pages/ForgotPasswordPage.vue'),
  },
  {
    path: '/reset-password/:uidb64/:token',
    component: () => import('pages/ResetPasswordPage.vue'),
  },
  {
    path: '/role-selection',
    component: () => import('pages/RoleSelectionPage.vue'),
  },
  {
    path: '/register/:role',
    component: () => import('pages/RegisterPage.vue'),
  },
  {
    path: '/verification',
    component: () => import('pages/VerificationPage.vue'),
  },
  // Add landing route
  {
    path: '/landing',
    component: () => import('pages/LandingPage.vue'),
  },
  {
    path: '/doctor-dashboard',
    component: () => import('pages/DoctorDashboard.vue'),
  },
  {
    path: '/doctor-appointments',
    name: 'DoctorAppointments',
    component: () => import('pages/DoctorAppointment.vue'),
  },
  {
    path: '/doctor-messaging',
    name: 'DoctorMessaging',
    component: () => import('pages/DoctorMessaging.vue'),
  },
  {
    path: '/doctor-settings',
    name: 'DoctorSettings',
    component: () => import('pages/DoctorSettings.vue'),
  },
  {
    path: '/doctor-predictive-analytics',
    name: 'DoctorPredictiveAnalytics',
    component: () => import('pages/DoctorPredictiveAnalytics.vue'),
  },
  {
    path: '/doctor-patient-management',
    name: 'DoctorPatientManagement',
    component: () => import('pages/DoctorPatientManagement.vue'),
  },
  {
    path: '/doctor-patient-archive',
    name: 'DoctorPatientArchive',
    component: () => import('pages/DoctorPatientArchive.vue'),
  },
  {
    path: '/nurse-dashboard',
    component: () => import('pages/NurseDashboard.vue'),
  },
  {
    path: '/nurse-patient-assessment',
    component: () => import('pages/NursePatientAssessment.vue'),
  },
  {
    path: '/nurse-patient-archive',
    name: 'NursePatientArchive',
    component: () => import('pages/NursePatientArchive.vue'),
  },
  {
    path: '/nurse-medicine-inventory',
    component: () => import('pages/NurseMedicineInventory.vue'),
  },
  {
    path: '/nurse-analytics',
    component: () => import('pages/NurseAnalytics.vue'),
  },
  {
    path: '/nurse-queue-management',
    component: () => import('pages/NurseQueueManagement.vue'),
  },
  {
    path: '/nurse-settings',
    component: () => import('pages/NurseSettings.vue'),
  },
  {
    path: '/nurse-messaging',
    component: () => import('pages/NurseMessaging.vue'),
  },
  {
    path: '/patient-dashboard',
    component: () => import('pages/PatientDashboard.vue'),
  },
  {
    path: '/patient-appointment-schedule',
    component: () => import('pages/PatientAppointmentSchedule.vue')
  },
  {
    path: '/patient-queue',
    component: () => import('pages/PatientQueue.vue')
  },
  {
    path: '/patient-notifications',
    component: () => import('pages/PatientNotifications.vue')
  },
  {
    path: '/patient-settings',
    component: () => import('pages/PatientSettings.vue')
  },
  {
    path: '/home',
    component: () => import('layouts/MainLayout.vue'),
    children: [{ path: '', component: () => import('pages/IndexPage.vue') }],
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;
