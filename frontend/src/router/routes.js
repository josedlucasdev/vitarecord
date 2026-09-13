const routes = [
  // Rutas públicas y de autenticación (AuthLayout: sin sidebar ni estado de usuario)
  {
    path: '/',
    component: () => import('layouts/AuthLayout.vue'),
    children: [
      {
        path: 'login',
        name: 'login',
        component: () => import('pages/auth/LoginPage.vue'),
        meta: { guestOnly: true }
      },
      {
        path: 'forgot-password',
        name: 'forgot-password',
        component: () => import('pages/auth/PasswordReset.vue'),
        meta: { guestOnly: true }
      },
      {
        path: 'reset-password',
        name: 'reset-password',
        component: () => import('pages/auth/PasswordReset.vue'),
        meta: { guestOnly: true }
      },
      {
        path: 'invitations/respond',
        name: 'doctor-invite-respond',
        component: () => import('pages/auth/DoctorInviteAction.vue')
      },
      {
        path: 'invitations/onboarding',
        name: 'doctor-onboarding',
        component: () => import('pages/auth/DoctorOnboarding.vue')
      },
      {
        path: 'doctors',
        name: 'public-doctors-directory',
        component: () => import('pages/public/DoctorsDirectory.vue')
      },
      {
        path: 'book-appointment',
        name: 'public-book-appointment',
        component: () => import('pages/appointments/BookAppointment.vue')
      },
      {
        path: 'patient/onboarding',
        name: 'patient-onboarding',
        component: () => import('pages/auth/PatientOnboarding.vue')
      }
    ]
  },

  // Rutas protegidas de la aplicación clínica (MainLayout: con navegación, sidebar y guardias ACL)
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('pages/IndexPage.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'admin/clinics',
        name: 'clinics-management',
        component: () => import('pages/admin/ClinicsManagement.vue'),
        meta: { requiresAuth: true, requiredPermission: 'tenants:provision' }
      },
      {
        path: 'admin/doctor-verification',
        name: 'doctor-verification',
        component: () => import('pages/admin/DoctorVerificationQueue.vue'),
        meta: { requiresAuth: true, requiredPermission: 'doctors:verify' }
      },
      {
        path: 'admin/control-tower',
        name: 'control-tower',
        component: () => import('pages/admin/ControlTower.vue'),
        meta: { requiresAuth: true, requiredPermission: 'emergency:monitor' }
      },
      {
        path: 'clinic/rooms',
        name: 'rooms-management',
        component: () => import('pages/clinic/RoomsManagement.vue'),
        meta: { requiresAuth: true, requiredPermission: 'rooms:read' }
      },
      {
        path: 'clinic/users',
        name: 'clinic-users-management',
        component: () => import('pages/clinic/ClinicUsersManagement.vue'),
        meta: { requiresAuth: true, requiredPermission: 'staff:manage' }
      },
      {
        path: 'doctor/schedule',
        name: 'doctor-schedule',
        component: () => import('pages/doctor/DoctorScheduleConfig.vue'),
        meta: { requiresAuth: true, requiredPermission: 'doctors:schedule_manage' }
      },
      {
        path: 'appointments/book',
        name: 'appointments-book',
        component: () => import('pages/appointments/BookAppointment.vue'),
        meta: { requiresAuth: true, requiredPermission: 'appointments:book' }
      },
      {
        path: 'appointments/my-list',
        name: 'appointments-my-list',
        component: () => import('pages/appointments/MyAppointments.vue'),
        meta: { requiresAuth: true, requiredPermission: 'appointments:manage' }
      },
      {
        path: 'clinic/cashier',
        name: 'cashier-management',
        component: () => import('pages/clinic/CashierManagement.vue'),
        meta: { requiresAuth: true, requiredPermission: 'payments:view_cashier' }
      },
      {
        path: 'medical/consultation',
        name: 'doctor-consultation',
        component: () => import('pages/doctor/DoctorConsultation.vue'),
        meta: { requiresAuth: true, requiredPermission: 'clinical_records:write' }
      },
      {
        path: 'medical/history',
        name: 'my-medical-history',
        component: () => import('pages/patient/MyMedicalHistory.vue'),
        meta: { requiresAuth: true, requiredPermission: 'clinical_records:read' }
      },
      {
        path: 'doctor/profile',
        name: 'doctor-profile',
        component: () => import('pages/doctor/DoctorProfile.vue'),
        meta: { requiresAuth: true }
      }
    ]
  },

  // Ruta pública para verificación de recetas farmacéuticas vía QR
  {
    path: '/verify-prescription/:hash',
    name: 'verify-prescription',
    component: () => import('pages/public/VerifyPrescription.vue')
  },

  // Manejo 404
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue')
  }
]

export default routes
