"""Tests d'intégration locale : authentification réelle, données fictives uniquement."""
import pytest
from sqlalchemy import select
from tests.factories import creer_utilisateur
from app.models.enums import RoleUtilisateur
from app.models.audit import AuditLog

pytestmark = pytest.mark.asyncio
PAYLOAD = {'laureat':'LAURÉAT TEST', 'distinction':'Meilleur coach test', 'equipe':'ÉQUIPE TEST', 'tournoi':'Tournoi fictif', 'organisateur':'Organisateur fictif'}

async def login(client, email):
    r = await client.post('/api/v1/auth/login', json={'email': email, 'mot_de_passe':'TestPassword123!'})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['access_token']}

async def test_roles_reels_jwt_creation_et_annulation(client, db_session):
    admin = await creer_utilisateur(db_session, RoleUtilisateur.ADMIN, 'admin-certif@example.com')
    await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, 'orga-certif@example.com')
    await creer_utilisateur(db_session, RoleUtilisateur.SUPPORTER, 'supporter-certif@example.com')
    await db_session.commit()
    admin_headers = await login(client, 'admin-certif@example.com')
    orga_headers = await login(client, 'orga-certif@example.com')
    supporter_headers = await login(client, 'supporter-certif@example.com')
    for headers, expected in [({}, 401), ({'Authorization':'Bearer jeton-falsifie'}, 401), (orga_headers, 403), (supporter_headers,403)]:
        assert (await client.post('/api/v1/admin/certificats', json=PAYLOAD, headers=headers)).status_code == expected
        assert (await client.get('/api/v1/admin/certificats', headers=headers)).status_code == expected
    r = await client.post('/api/v1/admin/certificats',json=PAYLOAD, headers=admin_headers)
    assert r.status_code == 201, r.text
    code = r.json()['code']
    assert (await client.get('/api/v1/certificats/'+code)).json()['statut'] == 'actif'
    for h, status in [({},401),(orga_headers,403),(supporter_headers,403)]:
        assert (await client.post('/api/v1/admin/certificats/'+code+'/annuler', json={'motif':'Test fictif'}, headers=h)).status_code == status
    r=await client.post('/api/v1/admin/certificats/'+code+'/annuler', json={'motif':'Test fictif'}, headers=admin_headers)
    assert r.status_code == 200 and r.json()['statut'] == 'annule'
    r=await client.get('/api/v1/certificats/'+code)
    assert r.status_code == 200 and r.json()['statut'] == 'annule' and 'no-store' in r.headers['cache-control']
    entries=(await db_session.execute(select(AuditLog).where(AuditLog.table_name == 'certificats_distinction').order_by(AuditLog.id))).scalars().all()
    assert len(entries)==2 and all(e.user_id==admin.id for e in entries)
    assert entries[-1].new_data['motif']=='Test fictif'
    admin.est_actif=False
    await db_session.commit()
    assert (await client.get('/api/v1/admin/certificats', headers=admin_headers)).status_code == 401

async def test_code_inconnu_et_donnees_non_valides(client, db_session):
    await creer_utilisateur(db_session, RoleUtilisateur.ADMIN, 'admin-2-certif@example.com')
    await db_session.commit()
    headers=await login(client, 'admin-2-certif@example.com')
    r=await client.get('/api/v1/certificats/'+'z'*32)
    assert r.status_code==404 and 'no-store' in r.headers['cache-control']
    assert (await client.post('/api/v1/admin/certificats', json={**PAYLOAD,'laureat':'  '},headers=headers)).status_code == 422
    assert (await client.post('/api/v1/admin/certificats', json={**PAYLOAD,'champ_surprise':'x'},headers=headers)).status_code == 422
