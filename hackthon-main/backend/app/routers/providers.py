"""F-07: Provider Console & Listing Management.

Provider portal endpoints: register as a provider, then CRUD your own
listings (see /api/providers/me/experiences)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_provider
from app.models.provider import Provider
from app.models.user import User, UserRole
from app.schemas.provider import ProviderCreate, ProviderOut


router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.post("/me", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def become_provider(
    payload: ProviderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProviderOut:
    existing = db.execute(select(Provider).where(Provider.user_id == user.id)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="provider profile already exists")

    provider = Provider(
        user_id=user.id,
        business_name=payload.business_name,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        description=payload.description,
    )
    db.add(provider)

    # Elevate role so subsequent provider-only routes accept the same token.
    if user.role != UserRole.ADMIN:
        user.role = UserRole.PROVIDER
        db.add(user)

    db.commit()
    db.refresh(provider)
    return ProviderOut.model_validate(provider)


@router.get("/me", response_model=ProviderOut)
def my_provider(
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> ProviderOut:
    provider = db.execute(select(Provider).where(Provider.user_id == user.id)).scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no provider profile")
    return ProviderOut.model_validate(provider)
