from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.hashing import hash_password, verify_password
from app.auth.jwt import create_access_token, create_refresh_token_raw, hash_refresh_token
from app.config import settings
from app.database import get_db
from app.models.enums import RoleUtilisateur
from app.models.user import RefreshToken, User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Authentification"])


def _role_value(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else user.role


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    access_token = create_access_token(user.id, _role_value(user))
    raw_refresh = create_refresh_token_raw()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Inscription supporter uniquement. Ne crée jamais de rôle staff."""
    email = str(payload.email).lower()
    existant = await db.execute(select(User).where(User.email == email))
    if existant.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail.")

    user = User(
        email=email,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
        role=RoleUtilisateur.SUPPORTER,
        nom_complet=payload.nom_complet.strip(),
        est_actif=True,
    )
    db.add(user)
    await db.flush()
    return await _issue_tokens(db, user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == str(payload.email).lower()))
    user = result.scalar_one_or_none()
    if user is None or not user.est_actif or not verify_password(payload.mot_de_passe, user.mot_de_passe_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect.")
    return await _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if stored is None or stored.revoked or stored.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token invalide ou expiré.")

    user = await db.get(User, stored.user_id)
    if user is None or not user.est_actif:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur introuvable ou désactivé.")

    stored.revoked = True
    new_raw = create_refresh_token_raw()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(new_raw),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    access_token = create_access_token(user.id, _role_value(user))
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=new_raw)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is not None:
        stored.revoked = True
        await db.commit()
    return None


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
