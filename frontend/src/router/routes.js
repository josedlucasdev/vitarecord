import { getValidTokenPayload } from 'src/composables/useAcl'

const routes = [
  // Rutas públicas y de autenticación (AuthLayout: sin sidebar ni estado de usuario)
  {
    path: '/',
    component: () => import('layouts/AuthLayout.vue'),
    children: [
      // Redirección de la raíz: si tiene sesión activa al dashboard, de lo contrario al login de pacientes
      {
        path: '',
        name: 'root',
        redirect: () => {
          const payload = getValidTokenPayload()
          if (payload) {
            return { name: 'home' }
          }
          return '/patient/login'
        }
      },

      // 1. Portal de Pacientes
      {
        path: 'patient/login',
        name: 'patient-login',
        component: () => import('pages/auth/PatientLogin.vue'),
        meta: { guestOnly: true, portal: 'patient', hideHeader: true }
      },
      {
        path: 'patient/forgot-password',
        name: 'patient-forgot-password',
        component: () => import('pages/auth/PasswordReset.vue'),
        meta: { guestOnly: true, portal: 'patient' }
      },
      {
        path: 'patient/reset-password',
        name: 'patient-reset-password',
        component: () => import('pages/auth/PasswordReset.vue'),
        meta: { guestOnly: true, portal: 'patient' }
      },

      // 2. Portal de Personal Clínico (Médicos, Admin Clínica, Recepción/Secretarias)
      {
        path: 'clinic/login',
        name: 'clinic-login',
        alias: ['staff/login'],
        component: () => import('pages/auth/ClinicStaffLogin.vue'),
        meta: { guestOnly: true, portal: 'clinic', hideHeader: true }
      },
      {
        path: 'clinic/forgot-password',
        name: 'clinic-forgot-password',
        component: () => import('pages/auth/PasswordReset.vue'),
        meta: { guestOnly: true, portal: 'clinic' }
      },
      {
        path: 'clinic/reset-password',
        name: 'clinic-reset-password',
        component: () => import('pages/auth/PasswordReset.vue'),
        meta: { guestOnly: true, portal: 'clinic' }
      },

      // 3. Portal Super Administrador del Sistema
      {
        path: 'admin/login',
        name: 'admin-login',
        alias: ['superadmin/login'],
        component: () => import('pages/auth/SuperAdminLogin.vue'),
        meta: { guestOnly: true, portal: 'admin', hideHeader: true }
      },
      {
        path: 'admin/forgot-password',
        name: 'admin-forgot-password',
        component: () => import('pages/auth/PasswordReset.vue'),
        meta: { guestOnly: true, portal: 'admin' }
      },
      {
        path: 'admin/reset-password',
        name: 'admin-reset-password',
        component: () => import('pages/auth/PasswordReset.vue'),
        meta: { guestOnly: true, portal: 'admin' }
      },

      // Redirecciones retrocompatibles
      {
        path: 'login',
        name: 'login',
        redirect: '/patient/login'
      },
      {
        path: 'forgot-password',
        name: 'forgot-password',
        redirect: '/patient/forgot-password'
      },
      {
        path: 'reset-password',
        name: 'reset-password',
        redirect: '/patient/reset-password'
      },

      // Rutas públicas adicionales
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
      },
      {
        path: 'privacy',
        name: 'privacy-policy',
        component: () => import('pages/public/PrivacyPolicy.vue')
      },
      {
        path: 'data-deletion',
        name: 'data-deletion',
        component: () => import('pages/public/DataDeletion.vue')
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
        path: 'dashboard',
        alias: ['home'],
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
        path: 'patient/profile',
        name: 'patient-profile',
        component: () => import('pages/patient/PatientProfile.vue'),
        meta: { requiresAuth: true }
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
