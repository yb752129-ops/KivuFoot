"""API HTTP minimale et isolée pour la démonstration de composition.

Ce serveur ne lit aucune base et ne contacte jamais la production. Il sert
uniquement à vérifier l'interface et le flux de sauvegarde dans le navigateur
avant un test sur une vraie base PostgreSQL de préproduction.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORT = 8765
BASE = "/api/v1"
TOKEN = "composition-demo-token"


def joueur(joueur_id: int, club_id: int, index: int, poste: str, statut: str = "actif", nom: str | None = None):
    return {
        "id": joueur_id,
        "nom_complet": nom or f"DEMO {('A' if club_id == 1 else 'B')} Joueur {index}",
        "date_naissance": "2000-01-01",
        "poste": poste,
        "statut": statut,
        "club_actuel_id": club_id,
        "numero": index,
        "photo_url": None,
    }


POSTES = ["gardien"] * 2 + ["defenseur"] * 6 + ["milieu"] * 6 + ["attaquant"] * 5
JOUEURS = []
for club_id in (1, 2):
    for index, poste in enumerate(POSTES, start=1):
        statut = "suspendu" if index == 18 else "actif"
        nom = None
        if index == 19:
            nom = f"DEMO {'A' if club_id == 1 else 'B'} Joueur avec un nom volontairement très long pour vérifier l affichage mobile"
        JOUEURS.append(joueur(1000 * club_id + index, club_id, index, poste, statut, nom))

STAFF = {
    1: [{"id": 501, "nom_complet": "Entraîneur principal DEMO A", "role": "entraineur_principal", "photo_url": None}],
    2: [{"id": 502, "nom_complet": "Entraîneur principal DEMO B", "role": "entraineur_principal", "photo_url": None}],
}
CLUBS = [
    {"id": 1, "nom": "DEMO Composition A", "ville": "Bukavu", "stade": "Terrain DEMO A", "logo_url": None, "est_demo": True, "coach_nom": "Coach composition DEMO"},
    {"id": 2, "nom": "DEMO Composition B", "ville": "Bukavu", "stade": "Terrain DEMO B", "logo_url": None, "est_demo": True, "coach_nom": "Coach B DEMO"},
]
MATCH = {
    "id": 9001,
    "saison_id": 1,
    "journee": "J1-DEMO",
    "date_heure": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
    "stade": "Terrain DEMO A",
    "equipe_domicile_id": 1,
    "equipe_exterieur_id": 2,
    "score_domicile": 0,
    "score_exterieur": 0,
    "statut": "programme",
    "started_at": None,
    "ended_at": None,
    "periode": None,
    "phase": "poule",
    "groupe": "A",
    "periode_started_at": None,
    "paused_at": None,
    "forfait": False,
    "forfait_equipe": None,
    "locked": False,
    "reglement_version_id": None,
    "resultat_retroactif": False,
    "motif_resultat_retroactif": None,
    "note_officielle": None,
    "buteurs_a_verifier": False,
}

COMPOSITIONS = {
    "domicile": {"club_id": 1, "club_nom": "DEMO Composition A", "logo_url": None, "formation": None, "staff": None, "titulaires": [], "banc": []},
    "exterieur": {"club_id": 2, "club_nom": "DEMO Composition B", "logo_url": None, "formation": None, "staff": None, "titulaires": [], "banc": []},
}


def json_response(handler: BaseHTTPRequestHandler, payload, status: int = 200):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def empty_response(handler: BaseHTTPRequestHandler, status: int = 204):
    handler.send_response(status)
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def require_auth(handler: BaseHTTPRequestHandler) -> bool:
    if handler.headers.get("Authorization") == f"Bearer {TOKEN}":
        return True
    json_response(handler, {"detail": "Session DEMO requise."}, 401)
    return False


def read_json(handler: BaseHTTPRequestHandler):
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        return json.loads(handler.rfile.read(length) or b"{}")
    except (ValueError, json.JSONDecodeError):
        return {}


def joueur_out(row, numero_override=None):
    return {
        "id": row["id"],
        "nom_complet": row["nom_complet"],
        "poste": row["poste"],
        "numero": row["numero"] if numero_override is None else numero_override,
        "photo_url": row.get("photo_url"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "KivuFootCompositionDemo/1.0"

    def log_message(self, fmt, *args):
        print(f"[demo-api] {self.address_string()} - {fmt % args}")

    def _path(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith(BASE):
            path = path[len(BASE):] or "/"
        return path, parse_qs(parsed.query)

    def do_GET(self):  # noqa: N802
        path, query = self._path()
        if path == "/competitions":
            return json_response(self, [{"id": 1, "nom": "DEMO - Composition professionnelle", "type": "championnat", "est_demo": True, "saison_label": "DEMO-COMPOSITION"}])
        if path == "/clubs":
            return json_response(self, CLUBS)
        if path.startswith("/clubs/") and path.endswith("/staff"):
            club_id = int(path.split("/")[2])
            return json_response(self, STAFF.get(club_id, []))
        if path.startswith("/clubs/"):
            club_id = int(path.split("/")[2])
            club = next((row for row in CLUBS if row["id"] == club_id), None)
            return json_response(self, club or {"detail": "Club introuvable."}, 200 if club else 404)
        if path == "/saisons":
            return json_response(self, [{"id": 1, "competition_id": 1, "nom": "Saison démo composition", "date_debut": "2026-01-01", "date_fin": "2026-12-31"}])
        if path == "/saisons/1/clubs":
            return json_response(self, CLUBS)
        if path == "/matchs":
            return json_response(self, [MATCH])
        if path == "/matchs/9001":
            return json_response(self, MATCH)
        if path == "/matchs/9001/composition":
            return json_response({"match_id": 9001, "max_remplacants": 7, "domicile": COMPOSITIONS["domicile"], "exterieur": COMPOSITIONS["exterieur"]})
        if path == "/joueurs":
            club_id = int(query.get("club_id", ["1"])[0])
            return json_response([row for row in JOUEURS if row["club_actuel_id"] == club_id])
        if path == "/matchs/9001/eligibilite":
            club_id = int(query.get("club_id", ["1"])[0])
            rows = []
            for row in JOUEURS:
                if row["club_actuel_id"] != club_id:
                    continue
                if row["statut"] == "suspendu":
                    rows.append({"joueur_id": row["id"], "joueur_nom": row["nom_complet"], "club_id": club_id, "statut": "BLOQUANT", "code": "suspendu", "message": "🔴 Joueur suspendu pour cette démonstration.", "sources": []})
                else:
                    rows.append({"joueur_id": row["id"], "joueur_nom": row["nom_complet"], "club_id": club_id, "statut": "OK", "code": "eligible", "message": "✅ Joueur éligible (DEMO).", "sources": []})
            return json_response(self, rows)
        if path == "/auth/me":
            if not require_auth(self):
                return
            return json_response(self, {"id": 900, "email": "coach.composition.demo@example.com", "nom_complet": "Coach composition DEMO", "role": "coach", "club_id": 1, "est_actif": True})
        return json_response(self, {"detail": f"Route DEMO non implémentée: {path}"}, 404)

    def do_POST(self):  # noqa: N802
        path, _ = self._path()
        if path == "/auth/login":
            payload = read_json(self)
            if payload.get("email") in {"coach.composition.demo@example.com", "manager.composition.demo@example.com"} and payload.get("mot_de_passe") == "ChangeMoiEnDemo123!":
                return json_response(self, {"access_token": TOKEN, "refresh_token": "composition-demo-refresh", "token_type": "bearer"})
            return json_response(self, {"detail": "Identifiants DEMO incorrects."}, 401)
        if path == "/auth/refresh":
            return json_response(self, {"access_token": TOKEN, "refresh_token": "composition-demo-refresh", "token_type": "bearer"})
        return json_response(self, {"detail": "Route DEMO non implémentée."}, 404)

    def do_PUT(self):  # noqa: N802
        path, _ = self._path()
        if path != "/matchs/9001/composition":
            return json_response(self, {"detail": "Route DEMO non implémentée."}, 404)
        if not require_auth(self):
            return
        payload = read_json(self)
        if payload.get("equipe") != "domicile":
            return json_response(self, {"detail": "Le compte DEMO ne gère que l'équipe domicile."}, 403)
        rows = payload.get("joueurs") or []
        titulaires = [row for row in rows if row.get("statut") == "titulaire"]
        if len(titulaires) != 11:
            return json_response(self, {"detail": "La composition DEMO doit contenir exactement 11 titulaires."}, 400)
        if len([row for row in rows if row.get("statut") == "remplacant"]) > 7:
            return json_response(self, {"detail": "Maximum 7 remplaçants."}, 400)
        ids = [row.get("joueur_id") for row in rows]
        if len(ids) != len(set(ids)):
            return json_response(self, {"detail": "Un même joueur ne peut apparaître qu'une seule fois."}, 400)
        numbers = [row.get("numero") for row in rows if row.get("numero") is not None]
        if len(numbers) != len(set(numbers)):
            return json_response(self, {"detail": "Le numéro de maillot est dupliqué."}, 400)
        player_by_id = {row["id"]: row for row in JOUEURS if row["club_actuel_id"] == 1}
        out = {"titulaires": [], "banc": []}
        for row in rows:
            current = player_by_id.get(row.get("joueur_id"))
            if not current:
                return json_response(self, {"detail": "Joueur DEMO inconnu ou hors club."}, 400)
            if current["statut"] == "suspendu":
                return json_response(self, {"detail": "🔴 Joueur suspendu pour cette démonstration."}, 400)
            value = joueur_out(current, row.get("numero"))
            out["titulaires" if row.get("statut") == "titulaire" else "banc"].append(value)
        staff_id = payload.get("staff_id")
        staff_row = next((row for row in STAFF[1] if row["id"] == staff_id), None)
        COMPOSITIONS["domicile"].update({
            "formation": payload.get("formation"),
            "staff": staff_row,
            "titulaires": out["titulaires"],
            "banc": out["banc"],
        })
        return json_response(self, {"match_id": 9001, "max_remplacants": 7, "domicile": COMPOSITIONS["domicile"], "exterieur": COMPOSITIONS["exterieur"]})

    def do_DELETE(self):  # noqa: N802
        path, _ = self._path()
        if path == "/auth/logout":
            return empty_response(self)
        return json_response(self, {"detail": "Route DEMO non implémentée."}, 404)


if __name__ == "__main__":
    print(f"API DEMO composition sur http://{HOST}:{PORT}{BASE}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
