import os
os.environ['DATABASE_URL']='sqlite+aiosqlite:///:memory:'
os.environ['SECRET_KEY']='test-local-aucune-cle-de-production'
import asyncio
from types import SimpleNamespace
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import get_db
from app.main import app
from app.auth.dependencies import get_current_user
from app.models.enums import RoleUtilisateur
from app.models.certificat import Certificat
from app.models.audit import AuditLog
from tests.sqlite_compat import utiliser_types_sqlite

async def main():
    engine=create_async_engine('sqlite+aiosqlite:///:memory:')
    restore=utiliser_types_sqlite([AuditLog.__table__])
    async with engine.begin() as c:
        await c.run_sync(lambda conn: Certificat.__table__.create(conn))
        await c.run_sync(lambda conn: AuditLog.__table__.create(conn))
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async with factory() as session:
        async def db_override(): yield session
        app.dependency_overrides[get_db]=db_override
        transport=ASGITransport(app=app,raise_app_exceptions=True)
        async with AsyncClient(transport=transport,base_url='http://test') as client:
            data={'laureat':'LAURÉAT TEST','distinction':'Meilleur coach test','equipe':'ÉQUIPE TEST','tournoi':'Tournoi fictif','organisateur':'Organisateur fictif'}
            r=await client.post('/api/v1/admin/certificats',json=data); assert r.status_code==401, r.text
            async def supporter(): return SimpleNamespace(id=2,role=RoleUtilisateur.SUPPORTER)
            app.dependency_overrides[get_current_user]=supporter
            r=await client.post('/api/v1/admin/certificats',json=data); assert r.status_code==403,r.text
            r=await client.get('/api/v1/admin/certificats'); assert r.status_code==403
            async def admin(): return SimpleNamespace(id=1,role=RoleUtilisateur.ADMIN)
            app.dependency_overrides[get_current_user]=admin
            r=await client.post('/api/v1/admin/certificats',json={**data,'laureat':'   '}); assert r.status_code==422
            r=await client.post('/api/v1/admin/certificats',json=data); assert r.status_code==201,r.text
            d=r.json(); code=d['code']; assert len(code)==32 and d['statut']=='actif'
            r2=await client.post('/api/v1/admin/certificats',json=data); assert r2.status_code==201 and r2.json()['code']!=code
            r=await client.get('/api/v1/certificats/'+code); assert r.status_code==200 and r.json()['laureat']=='LAURÉAT TEST' and r.json()['statut']=='actif' and 'no-store' in r.headers['cache-control']
            r=await client.get('/api/v1/certificats/inconnu'); assert r.status_code==404 and 'no-store' in r.headers['cache-control']
            r=await client.post('/api/v1/admin/certificats/'+code+'/annuler',json={'motif':'  '}); assert r.status_code==422
            r=await client.post('/api/v1/admin/certificats/'+code+'/annuler',json={'motif':'Erreur de saisie'}); assert r.status_code==200 and r.json()['statut']=='annule'
            r=await client.get('/api/v1/certificats/'+code); assert r.json()['statut']=='annule'
            r=await client.post('/api/v1/admin/certificats/'+code+'/annuler',json={'motif':'Nouvel essai'}); assert r.status_code==409
            rows=(await session.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all(); assert len(rows)==3 and rows[-1].new_data['motif']=='Erreur de saisie'
            app.dependency_overrides[get_current_user]=supporter
            assert (await client.post('/api/v1/admin/certificats/'+r2.json()['code']+'/annuler',json={'motif':'test'})).status_code==403
            print('OK: accès sans connexion 401; rôle interdit 403; création et données vides; références uniques; lecture active/inconnue/annulée; refus double annulation; audit création et annulation.')
    app.dependency_overrides.clear(); await engine.dispose(); restore()
asyncio.run(main())
