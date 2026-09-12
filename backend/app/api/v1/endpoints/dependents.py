from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.patient_dependent import PatientDependentCreate, PatientDependentPublic
from app.services.dependent_service import DependentService

router = APIRouter()


@router.get("/patients/me/dependents", response_model=list[PatientDependentPublic])
async def list_my_dependents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Consulta la lista de familiares/dependientes registrados por el paciente titular."""
    service = DependentService(db)
    return await service.list_dependents(current_user.id)


@router.post(
    "/patients/me/dependents",
    response_model=PatientDependentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def add_my_dependent(
    payload: PatientDependentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Registra un nuevo familiar dependiente asociado al paciente titular."""
    service = DependentService(db)
    return await service.add_dependent(current_user.id, payload)
