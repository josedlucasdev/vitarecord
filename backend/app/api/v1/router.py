from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    appointments,
    auth,
    availability,
    clinics,
    dependents,
    doctor_verification,
    doctors,
    emergencies,
    invitations,
    medical_records,
    notifications,
    payments,
    rooms,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(analytics.router, tags=["analytics"])
api_router.include_router(clinics.router, prefix="/clinics", tags=["clinics"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
api_router.include_router(invitations.router, tags=["invitations"])
api_router.include_router(doctor_verification.router, tags=["doctor-verification"])
api_router.include_router(rooms.router, tags=["rooms"])
api_router.include_router(availability.router, tags=["availability"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(dependents.router, tags=["dependents"])
api_router.include_router(payments.router, tags=["payments"])
api_router.include_router(emergencies.router, prefix="/emergencies", tags=["emergencies"])
api_router.include_router(medical_records.router, prefix="/medical-records", tags=["medical-records"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])


