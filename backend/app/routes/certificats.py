"""Vérification publique et gestion réservée à l'administrateur."""
import re
import secrets
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.rbac import require_roles
from app.database import get_db
from app.models.certificat import Certificat
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.user import User
from app.services.audit import log_audit

router = APIRouter(tags=['Certificats de distinction'])

class CertificatCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    laureat: str = Field(min_length=1, max_length=200)
    distinction: str = Field(min_length=1, max_length=200)
    equipe: str = Field(min_length=1, max_length=200)
    tournoi: str = Field(min_length=1, max_length=250)
    organisateur: str = Field(min_length=1, max_length=200)

class Annulation(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    motif: str = Field(min_length=3, max_length=500)

class CertificatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    laureat: str
    distinction: str
    equipe: str
    tournoi: str
    organisateur: str
    statut: str

@router.get('/certificats/{code}', response_model=CertificatOut)
async def verifier(code: str, response: Response, db: AsyncSession = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    if not re.fullmatch(r'[A-Za-z0-9_-]{32}', code):
        return JSONResponse(status_code=404, content={'detail': 'Certificat introuvable'}, headers={'Cache-Control': 'no-store, max-age=0'})
    obj = (await db.execute(select(Certificat).where(Certificat.code == code))).scalar_one_or_none()
    if obj is None:
        return JSONResponse(status_code=404, content={'detail': 'Certificat introuvable'}, headers={'Cache-Control': 'no-store, max-age=0'})
    return obj

@router.get('/admin/certificats', response_model=list[CertificatOut])
async def liste(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(RoleUtilisateur.ADMIN))):
    return (await db.execute(select(Certificat).order_by(Certificat.id.desc()).limit(200))).scalars().all()

@router.post('/admin/certificats', response_model=CertificatOut, status_code=status.HTTP_201_CREATED)
async def creer(payload: CertificatCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(RoleUtilisateur.ADMIN))):
    obj = Certificat(code=secrets.token_urlsafe(24), statut='actif', **payload.model_dump())
    db.add(obj)
    await db.flush()
    await log_audit(db, 'certificats_distinction', obj.id, ActionAudit.INSERT, user.id,
                    new_data={'code': obj.code, 'laureat': obj.laureat, 'distinction': obj.distinction, 'statut': obj.statut})
    await db.commit()
    await db.refresh(obj)
    return obj

@router.post('/admin/certificats/{code}/annuler', response_model=CertificatOut)
async def annuler(code: str, payload: Annulation, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(RoleUtilisateur.ADMIN))):
    obj = (await db.execute(select(Certificat).where(Certificat.code == code).with_for_update())).scalar_one_or_none()
    if obj is None:
        raise HTTPException(404, 'Certificat introuvable')
    if obj.statut != 'actif':
        raise HTTPException(409, 'Certificat déjà annulé')
    obj.statut = 'annule'
    await log_audit(db, 'certificats_distinction', obj.id, ActionAudit.UPDATE, user.id,
                    old_data={'statut': 'actif'}, new_data={'statut': 'annule', 'motif': payload.motif})
    await db.commit()
    await db.refresh(obj)
    return obj
