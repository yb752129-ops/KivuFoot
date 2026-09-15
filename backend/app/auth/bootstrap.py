"""Bootstrap du premier admin — à usage unique, conditionnel et audité.

Pourquoi : le championnat doit pouvoir être programmé même quand aucun
compte staff n'existe encore et que la clef service Supabase n'est pas
disponible sur le téléphone du responsable.

Règles de sécurité non négociables :
- ne fait RIEN si un compte staff (admin ou organisateur) existe déjà ;
- ne fait RIEN si le compte cible n'existe pas ;
- ne touche aucun autre compte ;
- journalise la transformation dans la table d'audit ;
- une fois un staff présent, ce code est inerte pour toujours.
"""
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.user import User
from app.services.audit import log_audit

EMAIL_CIBLE = "yb752129@gmail.com"
ROLES_STAFF = (RoleUtilisateur.ADMIN.value, RoleUtilisateur.ORGANISATEUR.value)


async def bootstrap_premier_admin() -> None:
    async with AsyncSessionLocal() as db:
        staff = await db.execute(
            select(User.id).where(User.role.in_(ROLES_STAFF)).limit(1)
        )
        if staff.scalar_one_or_none() is not None:
            return
        result = await db.execute(select(User).where(User.email == EMAIL_CIBLE))
        user = result.scalar_one_or_none()
        if user is None:
            return
        avant = user.role
        user.role = RoleUtilisateur.ADMIN
        user.est_actif = True
        await log_audit(
            db,
            "users",
            user.id,
            ActionAudit.UPDATE,
            None,
            {"role": avant},
            {"role": RoleUtilisateur.ADMIN.value,
             "motif": "bootstrap premier admin : aucun staff présent au démarrage"},
        )
        await db.commit()
