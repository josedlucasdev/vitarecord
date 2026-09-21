"""Inicializacion automatica de tablas y usuarios semilla en desarrollo."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.base import Base
from app.models.clinic import Clinic, ClinicRoom
from app.models.affiliation import DoctorClinicAffiliation
from app.models.user import User

logger = logging.getLogger("seed")


async def init_db_and_seed() -> None:
    """Crea las tablas si no existen y puebla datos iniciales de prueba."""
    async with engine.begin() as conn:
        # Crea tablas registradas en Base.metadata si aun no existen
        await conn.run_sync(Base.metadata.create_all)

        # Asegurar columnas en la tabla clinics
        for col_def in [
            "ADD COLUMN phone VARCHAR(32) NULL",
            "ADD COLUMN address VARCHAR(255) NULL",
            "ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE",
        ]:
            try:
                await conn.exec_driver_sql(f"ALTER TABLE clinics {col_def}")
            except Exception:
                pass  # Columna ya existe

        # Asegurar columnas de perfil profesional y datos de paciente en la tabla users
        for col_def in [
            "ADD COLUMN academic_degrees JSON NULL",
            "ADD COLUMN work_experience JSON NULL",
            "ADD COLUMN is_public_profile_enabled BOOLEAN NOT NULL DEFAULT TRUE",
            "ADD COLUMN profile_picture_url VARCHAR(500) NULL",
            "ADD COLUMN identification_number VARCHAR(32) NULL",
            "ADD COLUMN birth_date DATETIME NULL",
            "ADD COLUMN gender VARCHAR(16) NULL",
            "ADD COLUMN address VARCHAR(255) NULL",
            "ADD COLUMN city VARCHAR(100) NULL",
            "ADD COLUMN country VARCHAR(100) NULL DEFAULT 'Venezuela'",
            "ADD COLUMN blood_type VARCHAR(10) NULL",
            "ADD COLUMN height_cm FLOAT NULL",
            "ADD COLUMN allergies VARCHAR(500) NULL",
            "ADD COLUMN chronic_conditions VARCHAR(500) NULL",
            "ADD COLUMN emergency_contact_name VARCHAR(255) NULL",
            "ADD COLUMN emergency_contact_phone VARCHAR(32) NULL",
            "ADD COLUMN emergency_contact_relationship VARCHAR(100) NULL",
        ]:
            try:
                await conn.exec_driver_sql(f"ALTER TABLE users {col_def}")
            except Exception:
                pass  # Columna ya existe

        # Asegurar columnas de consultorios (salas físicas)
        for col_def in [
            "ADD COLUMN specialty VARCHAR(100) NULL",
            "ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'",
            "ADD COLUMN operating_hours JSON NULL",
        ]:
            try:
                await conn.exec_driver_sql(f"ALTER TABLE clinic_rooms {col_def}")
            except Exception:
                pass  # Columna ya existe

        # Asegurar columna intake_data en tabla appointments
        try:
            await conn.exec_driver_sql("ALTER TABLE appointments ADD COLUMN intake_data JSON NULL")
        except Exception:
            pass

        # Asegurar columnas para el Módulo 6 en notification_logs
        for col_def in [
            "ADD COLUMN appointment_id VARCHAR(36) NULL",
            "ADD COLUMN external_message_id VARCHAR(500) NULL",
            "ADD COLUMN metadata_payload JSON NULL",
            "ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT FALSE",
            "ADD COLUMN read_at DATETIME NULL",
        ]:
            try:
                await conn.exec_driver_sql(f"ALTER TABLE notification_logs {col_def}")
            except Exception:
                pass

        # Asegurar columnas de tipo de contrato y honorarios en doctor_clinic_affiliations
        for col_def in [
            "ADD COLUMN contract_type VARCHAR(32) NOT NULL DEFAULT 'INDEPENDENT'",
            "ADD COLUMN consultation_fee DECIMAL(10,2) NOT NULL DEFAULT 30.00",
            "ADD COLUMN currency VARCHAR(8) NOT NULL DEFAULT 'USD'",
        ]:
            try:
                await conn.exec_driver_sql(f"ALTER TABLE doctor_clinic_affiliations {col_def}")
            except Exception:
                pass  # Columna ya existe

    async with AsyncSessionLocal() as db:
        # Verificar si ya existe el usuario superadmin
        stmt = select(User).where(User.email == "admin@intimasalud.com")
        existing_admin = (await db.execute(stmt)).scalar_one_or_none()
        if existing_admin:
            logger.info("Base de datos ya cuenta con datos semilla. Enriqueciendo perfiles médicos, consultorios y procedimientos...")
            await enrich_doctors_profiles(db)
            await enrich_clinic_rooms(db)
            await enrich_procedures(db)
            return

        logger.info("Poblando base de datos con usuarios y clinica de prueba...")


        # 1. Cinco Clínicas / Sedes Principales
        clinics_data = [
            ("c1111111-1111-1111-1111-111111111111", "Clínica ÍntimaSalud Central (Sede Principal)", "intimasalud-central", "America/Caracas", "VE"),
            ("c2222222-2222-2222-2222-222222222222", "Clínica ÍntimaSalud Norte (Sede Chacao)", "intimasalud-norte", "America/Caracas", "VE"),
            ("c3333333-3333-3333-3333-333333333333", "Clínica ÍntimaSalud Este (Sede Las Mercedes)", "intimasalud-este", "America/Caracas", "VE"),
            ("c4444444-4444-4444-4444-444444444444", "Clínica ÍntimaSalud Oeste (Sede San Bernardino)", "intimasalud-oeste", "America/Caracas", "VE"),
            ("c5555555-5555-5555-5555-555555555555", "Clínica ÍntimaSalud Valencia (Sede El Viñedo)", "intimasalud-valencia", "America/Caracas", "VE"),
        ]

        created_clinics = []
        for cid, cname, cslug, ctz, ccountry in clinics_data:
            c = Clinic(
                id=cid,
                name=cname,
                slug=cslug,
                timezone=ctz,
                country_code=ccountry,
                is_active=True,
            )
            db.add(c)
            created_clinics.append(c)

            # Consultorios de la sede con especialidad y estado
            rooms_seed_config = [
                (1, "101", "Ginecología & Obstetricia", "Consultorio Gineco-Obstétrico"),
                (2, "201", "Medicina Materno-Fetal", "Consultorio de Alto Riesgo y Ecografía"),
                (3, "301", None, "Consultorio Polivalente Multifuncional"),
            ]
            for r_idx, r_num, r_spec, r_desc in rooms_seed_config:
                room = ClinicRoom(
                    id=f"r{cid[1:8]}-{cid[9:13]}-{cid[14:18]}-{cid[19:23]}-{cid[24:35]}{r_idx}",
                    clinic_id=cid,
                    name=f"Consultorio {r_num} - {cname.split('(')[0].strip()}",
                    room_number=r_num,
                    specialty=r_spec,
                    status="ACTIVE",
                    operating_hours={"start": "07:00", "end": "19:00"},
                    description=r_desc,
                    is_active=True,
                )
                db.add(room)
        await db.flush()
        clinic = created_clinics[0]

        default_hashed = hash_password("Password123!")

        # 2. SuperAdmin (sin MFA obligatorio para acceso rapido en dev)
        admin = User(
            id="u1111111-1111-1111-1111-111111111111",
            email="admin@intimasalud.com",
            phone="+584120000001",
            hashed_password=default_hashed,
            role="SUPERADMIN",
            status="ACTIVE",
            mfa_enabled=False,
        )
        db.add(admin)

        # 3. 20 Médicos Especialistas con Multi-Afiliación
        from datetime import time as dt_time
        from app.models.schedule import DoctorWeeklySchedule

        doctors_spec = [
            ("u2222222-2222-2222-2222-222222222222", "doctor@intimasalud.com", "Dr. Alejandro Morales", "Ginecología & Obstetricia", "+584120000002", [0, 1, 4]),
            ("u2222222-2222-2222-2222-222222222223", "dra.castillo@intimasalud.com", "Dra. Valentina Castillo", "Medicina Materno-Fetal", "+584120000023", [0, 1, 2]),
            ("u2222222-2222-2222-2222-222222222224", "dr.silva@intimasalud.com", "Dr. Roberto Silva", "Fertilidad & Reproducción Asistida", "+584120000024", [0, 2, 3]),
            ("u2222222-2222-2222-2222-222222222225", "dra.mendoza@intimasalud.com", "Dra. Sofía Mendoza", "Ginecología Oncológica", "+584120000025", [0, 1, 4]),
            ("u2222222-2222-2222-2222-222222222226", "dr.navarro@intimasalud.com", "Dr. Gabriel Navarro", "Mastología & Patología Mamaria", "+584120000026", [0, 2, 3]),
            ("u2222222-2222-2222-2222-222222222227", "dra.vargas@intimasalud.com", "Dra. Camila Vargas", "Endocrinología Ginecológica", "+584120000027", [0, 2, 4]),
            ("u2222222-2222-2222-2222-222222222228", "dr.benitez@intimasalud.com", "Dr. Andrés Benítez", "Urología Ginecológica & Piso Pélvico", "+584120000028", [0, 1, 3]),
            ("u2222222-2222-2222-2222-222222222229", "dra.duarte@intimasalud.com", "Dra. Mariana Duarte", "Perinatología & Alto Riesgo", "+584120000029", [0, 1, 3]),
            ("u2222222-2222-2222-2222-222222222230", "dr.paredes@intimasalud.com", "Dr. Fernando Paredes", "Cirugía Laparoscópica Ginecológica", "+584120000030", [0, 1, 3]),
            ("u2222222-2222-2222-2222-222222222231", "dra.rangel@intimasalud.com", "Dra. Lucía Rangel", "Ginecología Infantojuvenil", "+584120000031", [0, 1, 4]),
            ("u2222222-2222-2222-2222-222222222232", "dr.pena@intimasalud.com", "Dr. Carlos Eduardo Peña", "Andrología & Salud Reproductiva", "+584120000032", [0, 2, 3]),
            ("u2222222-2222-2222-2222-222222222233", "dra.quintana@intimasalud.com", "Dra. Beatriz Quintana", "Ecografía Genética 3D/4D", "+584120000033", [0, 1, 2]),
            ("u2222222-2222-2222-2222-222222222234", "dr.cardenas@intimasalud.com", "Dr. Javier Cárdenas", "Oncología Pélvica Avanzada", "+584120000034", [1, 2, 3]),
            ("u2222222-2222-2222-2222-222222222235", "dra.salazar@intimasalud.com", "Dra. Natalia Salazar", "Planificación Familiar & Anticoncepción", "+584120000035", [1, 2, 4]),
            ("u2222222-2222-2222-2222-222222222236", "dr.arismendi@intimasalud.com", "Dr. Daniel Arismendi", "Urodinamia & Incontinencia Urinaria", "+584120000036", [1, 3, 4]),
            ("u2222222-2222-2222-2222-222222222237", "dra.briceno@intimasalud.com", "Dra. Andrea Briceño", "Ginecología Estética & Regenerativa", "+584120000037", [2, 3, 4]),
            ("u2222222-2222-2222-2222-222222222238", "dr.villalobos@intimasalud.com", "Dr. Héctor Villalobos", "Medicina Fetal & Tamizaje", "+584120000038", [2, 3, 4]),
            ("u2222222-2222-2222-2222-222222222239", "dra.colmenares@intimasalud.com", "Dra. Patricia Colmenares", "Menopausia & Terapia Hormonal", "+584120000039", [2, 3, 4]),
            ("u2222222-2222-2222-2222-222222222240", "dr.sotomayor@intimasalud.com", "Dr. Manuel Sotomayor", "Inmunología de la Reproducción", "+584120000040", [3, 4, 1]),
            ("u2222222-2222-2222-2222-222222222241", "dra.carrizo@intimasalud.com", "Dra. Isabel Carrizo", "Genética Médica & Consejo Prenatal", "+584120000041", [3, 4, 2]),
        ]

        for doc_id, email, name, spec, phone, clinic_indices in doctors_spec:
            doc = User(
                id=doc_id,
                email=email,
                full_name=name,
                specialty=spec,
                phone=phone,
                hashed_password=default_hashed,
                role="DOCTOR",
                status="ACTIVE",
                license_verification_status="VERIFIED",
                is_available_for_emergencies=True,
                mfa_enabled=False,
            )
            db.add(doc)
            await db.flush()

            for c_idx in clinic_indices:
                target_clinic = created_clinics[c_idx]
                aff = DoctorClinicAffiliation(
                    doctor_id=doc.id,
                    clinic_id=target_clinic.id,
                    status="ACTIVE",
                )
                db.add(aff)

                # Horario semanal de Lunes a Domingo (08:00 a 17:00)
                for day in range(7):
                    sched = DoctorWeeklySchedule(
                        doctor_id=doc.id,
                        clinic_id=target_clinic.id,
                        day_of_week=day,
                        start_time=dt_time(8, 0),
                        end_time=dt_time(17, 0),
                        slot_duration_minutes=30,
                        is_active=True,
                    )
                    db.add(sched)

        # 4. Administrador de Clínica / Tenant
        clinic_admin = User(
            id="u6666666-6666-6666-6666-666666666666",
            email="clinic.admin@intimasalud.com",
            full_name="Lic. Carlos Mendoza (Admin Clínica)",
            phone="+584120000006",
            hashed_password=default_hashed,
            role="CLINIC_ADMIN",
            status="ACTIVE",
            clinic_id=clinic.id,
            mfa_enabled=False,
        )
        db.add(clinic_admin)

        # 5. Moderador / Compliance Reviewer (Staff Global)
        moderator = User(
            id="u7777777-7777-7777-7777-777777777777",
            email="moderador@intimasalud.com",
            full_name="Dra. Elena Rivas (Cumplimiento)",
            phone="+584120000007",
            hashed_password=default_hashed,
            role="COMPLIANCE_REVIEWER",
            status="ACTIVE",
            clinic_id=None,
            mfa_enabled=False,
        )
        db.add(moderator)

        # 6. Recepcionista / Secretaria de Sede
        reception = User(
            id="u3333333-3333-3333-3333-333333333333",
            email="recepcion@intimasalud.com",
            full_name="Ana Gómez (Recepción)",
            phone="+584120000003",
            hashed_password=default_hashed,
            role="RECEPTIONIST",
            status="ACTIVE",
            clinic_id=clinic.id,
            mfa_enabled=False,
        )
        db.add(reception)

        # 7. Paciente Titular
        patient = User(
            id="u4444444-4444-4444-4444-444444444444",
            email="paciente@intimasalud.com",
            full_name="Lucía Rodríguez (Paciente)",
            phone="+584120000004",
            hashed_password=default_hashed,
            role="PATIENT",
            status="ACTIVE",
            mfa_enabled=False,
        )
        db.add(patient)

        # 8. SuperAdmin con MFA habilitado
        mfa_admin = User(
            id="u5555555-5555-5555-5555-555555555555",
            email="mfa.admin@intimasalud.com",
            full_name="SuperAdmin con MFA",
            phone="+584120000005",
            hashed_password=default_hashed,
            role="SUPERADMIN",
            status="ACTIVE",
            mfa_enabled=True,
            mfa_secret="JBSWY3DPEHPK3PXP",
        )
        db.add(mfa_admin)

        await db.commit()
        logger.info("Datos semilla creados exitosamente.")
        await enrich_doctors_profiles(db)


async def enrich_doctors_profiles(db: AsyncSession) -> None:
    """Enriquece los médicos existentes con títulos académicos, experiencia laboral y biografía si no los tienen."""
    sample_profiles = {
        "Dr. Alejandro Morales": {
            "biography": "Especialista en Ginecología y Obstetricia con más de 12 años de trayectoria. Enfocado en salud integral de la mujer, control de embarazo de alto riesgo y cirugía ginecológica mínimamente invasiva.",
            "academic_degrees": [
                {"title": "Médico Cirujano", "institution": "Universidad Central de Venezuela (UCV)", "year": 2011, "license_or_id": "MPPS-12948"},
                {"title": "Especialista en Obstetricia y Ginecología", "institution": "Hospital Universitario de Caracas", "year": 2015, "license_or_id": "CMDF-8392"},
                {"title": "Diplomado en Laparoscopia Ginecológica", "institution": "Sociedad Internacional de Cirugía Mínimamente Invasiva", "year": 2018},
            ],
            "work_experience": [
                {"position": "Jefe de Servicio de Ginecología", "workplace": "Clínica ÍntimaSalud Central", "start_year": 2019, "end_year": None, "description": "Coordinación del área quirúrgica ginecológica y consulta especializada."},
                {"position": "Médico Especialista Adjunto", "workplace": "Hospital Materno Infantil", "start_year": 2015, "end_year": 2019, "description": "Atención de partos de alto riesgo, urgencias obstétricas e intervenciones laparoscópicas."},
            ],
        },
        "Dra. Valentina Castillo": {
            "biography": "Especialista en Medicina Materno-Fetal con amplia experiencia en diagnóstico prenatal de precisión, ecografía morfológica avanzada y manejo de gestaciones múltiples.",
            "academic_degrees": [
                {"title": "Médico Cirujano (Magna Cum Laude)", "institution": "Universidad de Los Andes (ULA)", "year": 2013, "license_or_id": "MPPS-14832"},
                {"title": "Especialidad en Ginecología y Obstetricia", "institution": "Maternidad Concepción Palacios", "year": 2017, "license_or_id": "CMDF-9941"},
                {"title": "Fellowship en Medicina Fetal", "institution": "Instituto Valenciano de Fertilidad", "year": 2019},
            ],
            "work_experience": [
                {"position": "Especialista en Medicina Fetal", "workplace": "Clínica ÍntimaSalud Norte", "start_year": 2020, "end_year": None, "description": "Ecografía genética del primer trimestre y neurosonografía fetal."},
                {"position": "Adjunta del Servicio de Alto Riesgo Obstétrico", "workplace": "Hospital Clínico", "start_year": 2017, "end_year": 2020, "description": "Supervisión de partos complicados y tamizaje fetal."},
            ],
        },
        "Dr. Roberto Silva": {
            "biography": "Experto en Fertilidad y Reproducción Asistida. Dedicado al estudio y tratamiento de la pareja infértil, técnicas de baja y alta complejidad y preservación de fertilidad.",
            "academic_degrees": [
                {"title": "Médico Cirujano", "institution": "Universidad de Carabobo (UC)", "year": 2010, "license_or_id": "MPPS-11504"},
                {"title": "Especialista en Ginecología", "institution": "Hospital Central de Valencia", "year": 2014, "license_or_id": "CMDC-7412"},
                {"title": "Master en Reproducción Humana Asistida", "institution": "Universidad Complutense de Madrid", "year": 2016},
            ],
            "work_experience": [
                {"position": "Director de Unidad de Fertilidad", "workplace": "Clínica ÍntimaSalud Este", "start_year": 2018, "end_year": None, "description": "Protocolos de estimulación ovárica y procedimientos FIV."},
            ],
        },
        "Dra. Sofía Mendoza": {
            "biography": "Ginecóloga Oncóloga especializada en la prevención, diagnóstico temprano y tratamiento quirúrgico de lesiones premalignas y neoplasias del tracto genital femenino.",
            "academic_degrees": [
                {"title": "Médico Cirujano", "institution": "Universidad Central de Venezuela (UCV)", "year": 2012, "license_or_id": "MPPS-13840"},
                {"title": "Especialista en Oncología Ginecológica", "institution": "Instituto Oncológico Luis Razetti", "year": 2017, "license_or_id": "CMDF-10492"},
            ],
            "work_experience": [
                {"position": "Cirujana Oncóloga Ginecológica", "workplace": "Clínica ÍntimaSalud Central", "start_year": 2019, "end_year": None, "description": "Colposcopia avanzada, conizaciones y cirugía oncológica pélvica."},
            ],
        },
    }

    stmt = select(User).where(User.role == "DOCTOR", User.status == "ACTIVE")
    res = await db.execute(stmt)
    doctors = list(res.scalars().all())

    modified = False
    for doc in doctors:
        data = sample_profiles.get(doc.full_name)
        if not data:
            # Perfil genérico si no está en sample_profiles específicos
            data = {
                "biography": f"Facultativo especialista en {doc.specialty}. Miembro titular de sociedades científicas con sólida vocación de servicio y atención personalizada.",
                "academic_degrees": [
                    {"title": f"Médico Cirujano", "institution": "Universidad Central de Venezuela", "year": 2012, "license_or_id": doc.license_number or "MPPS-15021"},
                    {"title": f"Especialista en {doc.specialty}", "institution": "Hospital Docente Clínico", "year": 2016, "license_or_id": "CMD-8291"},
                ],
                "work_experience": [
                    {"position": f"Especialista en {doc.specialty}", "workplace": "Red Médica VitaRecord", "start_year": 2018, "end_year": None, "description": "Consulta ambulatoria, procedimientos preventivos y seguimiento clínico."},
                ],
            }

        # Si aún no tiene títulos o biografía configurados, enriquecer
        if not doc.academic_degrees or len(doc.academic_degrees) == 0:
            doc.academic_degrees = data["academic_degrees"]
            modified = True
        if not doc.work_experience or len(doc.work_experience) == 0:
            doc.work_experience = data["work_experience"]
            modified = True
        if not doc.biography:
            doc.biography = data["biography"]
            modified = True
        doc.is_public_profile_enabled = True

    if modified:
        await db.commit()
        logger.info("Perfiles de médicos enriquecidos con títulos y experiencia exitosamente.")


async def enrich_clinic_rooms(db: AsyncSession) -> None:
    """Enriquece consultorios existentes con especialidades y estado para migraciones limpias."""
    from app.models.clinic import ClinicRoom, RoomScheduleLock
    from sqlalchemy import select

    stmt = select(ClinicRoom)
    res = await db.execute(stmt)
    rooms = list(res.scalars().all())

    modified = False
    for r in rooms:
        # Asegurar status por defecto
        if not getattr(r, "status", None):
            r.status = "ACTIVE"
            modified = True
        # Asegurar horario por defecto
        if not getattr(r, "operating_hours", None):
            r.operating_hours = {"start": "07:00", "end": "19:00"}
            modified = True
        # Asignar especialidad según nombre o número si no tiene
        if not getattr(r, "specialty", None):
            if "101" in (r.room_number or "") or "1" in (r.name or ""):
                r.specialty = "Ginecología & Obstetricia"
            elif "201" in (r.room_number or "") or "2" in (r.name or ""):
                r.specialty = "Medicina Materno-Fetal"
            else:
                r.specialty = None  # Polivalente
            modified = True

        # Asegurar cerrojo mutex en room_schedule_locks
        from sqlalchemy import text
        try:
            await db.execute(
                text("INSERT IGNORE INTO room_schedule_locks (room_id) VALUES (:rid)"),
                {"rid": r.id},
            )
        except Exception:
            pass

    if modified:
        await db.commit()
        logger.info("Consultorios físicos enriquecidos con especialidades y estado exitosamente.")


async def enrich_procedures(db: AsyncSession) -> None:
    """Asegura la existencia de catálogo de procedimientos y actualiza afiliaciones existentes."""
    from decimal import Decimal
    from app.models.clinic import Clinic
    from app.models.affiliation import DoctorClinicAffiliation
    from app.models.procedure import MedicalProcedure

    # 1. Asegurar valores por defecto en DoctorClinicAffiliation
    aff_res = await db.execute(select(DoctorClinicAffiliation))
    affiliations = list(aff_res.scalars().all())
    aff_modified = False
    for aff in affiliations:
        if not getattr(aff, "contract_type", None):
            aff.contract_type = "INDEPENDENT"
            aff_modified = True
        if getattr(aff, "consultation_fee", None) is None:
            aff.consultation_fee = Decimal("30.00")
            aff_modified = True
        if not getattr(aff, "currency", None):
            aff.currency = "USD"
            aff_modified = True
    if aff_modified:
        await db.commit()

    # 2. Catálogo institucional de procedimientos para cada clínica
    cl_res = await db.execute(select(Clinic))
    clinics = list(cl_res.scalars().all())
    if not clinics:
        return

    sample_procedures = [
        ("Ecografía Pélvica / Transvaginal", "Evaluación ginecológica y pélvica de alta resolución", Decimal("35.00"), 20, "Ecografía"),
        ("Colposcopia y Vulvoscopia", "Evaluación óptica amplificada del cuello uterino", Decimal("40.00"), 25, "Diagnóstico"),
        ("Citología Cervical (Papanicolaou)", "Toma de muestra celular para despistaje oncológico", Decimal("15.00"), 10, "Laboratorio"),
        ("Biopsia de Cuello Uterino", "Toma de tejido cervical dirigida para estudio histopatológico", Decimal("50.00"), 30, "Procedimiento Quirúrgico Menor"),
        ("Cauterización de Lesión Cervical", "Tratamiento de ectopia o lesiones benignas", Decimal("60.00"), 30, "Procedimiento Quirúrgico Menor"),
        ("Inserción / Retiro de DIU", "Colocación o extracción de dispositivo intrauterino", Decimal("45.00"), 20, "Planificación Familiar"),
    ]

    added = False
    for cl in clinics:
        p_res = await db.execute(select(MedicalProcedure).where(MedicalProcedure.clinic_id == cl.id))
        existing_procs = list(p_res.scalars().all())
        if not existing_procs:
            for name, desc, price, dur, cat in sample_procedures:
                proc = MedicalProcedure(
                    clinic_id=cl.id,
                    doctor_id=None,  # Catálogo institucional regulado por la clínica
                    name=name,
                    description=desc,
                    price=price,
                    currency="USD",
                    duration_minutes=dur,
                    category=cat,
                    is_active=True,
                )
                db.add(proc)
                added = True

    if added:
        await db.commit()
        logger.info("Catálogo de procedimientos clínicos inicializado exitosamente.")


