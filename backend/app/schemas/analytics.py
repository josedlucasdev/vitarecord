import datetime
from decimal import Decimal
from pydantic import BaseModel


class ClinicKpis(BaseModel):
    total_appointments: int
    completed_appointments: int
    confirmed_appointments: int
    pending_appointments: int
    cancelled_appointments: int
    attendance_rate_pct: float
    total_revenue: Decimal
    total_paid_count: int
    unique_patients: int
    active_doctors: int
    active_rooms: int


class DailyTrendItem(BaseModel):
    date: str
    total: int
    confirmed: int
    completed: int
    cancelled: int


class StatusDistributionItem(BaseModel):
    status: str
    label: str
    count: int
    percentage: float
    color: str


class PaymentMethodItem(BaseModel):
    method: str
    label: str
    amount: Decimal
    count: int
    color: str


class SpecialtyItem(BaseModel):
    specialty: str
    count: int


class DoctorPerformanceItem(BaseModel):
    doctor_id: str
    doctor_name: str
    specialty: str | None = None
    appointments_count: int
    completed_count: int


class RoomUtilizationItem(BaseModel):
    room_id: str
    room_name: str
    appointments_count: int


class TodayAppointmentItem(BaseModel):
    id: str
    start_time: str
    patient_name: str = "Paciente"
    doctor_name: str = "Dr. Especialista"
    specialty: str | None = None
    room_name: str | None = None
    status: str
    payment_status: str | None = None
    amount: Decimal | None = None


class ClinicAnalyticsResponse(BaseModel):
    clinic_id: str
    clinic_name: str
    period_days: int
    kpis: ClinicKpis
    trends: list[DailyTrendItem]
    status_distribution: list[StatusDistributionItem]
    payment_methods: list[PaymentMethodItem]
    specialties: list[SpecialtyItem]
    top_doctors: list[DoctorPerformanceItem]
    room_utilization: list[RoomUtilizationItem]
    today_appointments: list[TodayAppointmentItem]
