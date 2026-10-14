# KivuFoot — contrôle d'identité avant publication PDF

## Logo

Le logo complet KivuFoot a été retrouvé et vérifié dans les éléments déjà
partagés :

- source visuelle : `frontend-web/public/icone-512.png` ;
- copie embarquée par le backend : `backend/app/assets/kivufoot-logo.png` ;
- les deux fichiers ont le même SHA-256 :
  `55a5e346d9aea68c01da6ec3cf75aaf4d07be9c8637341442ab430bb87b7eaa0` ;
- `favicon.svg` et `kivufoot-mark.svg` restent des marques carrées et ne sont
  pas utilisés comme logo principal du PDF.

Le générateur utilise automatiquement la copie backend confirmée lorsque
`PDF_LOGO_PATH` est vide. Il est possible de fournir un autre chemin seulement
après validation explicite de ce fichier.

## Coordonnées confirmées

La source partagée qui confirme les coordonnées est :

`/home/user/KivuFoot_proposition_fiches_performance.pdf`, page 2,
« Proposition de collaboration — Fiches individuelles de performance », datée
« Bujumbura, le 9 octobre 2026 » et signée « Yves Bukasa, Porteur et
concepteur de KivuFoot ». Cette mention est la date et le lieu de la pièce qui
confirme les coordonnées ; elle ne définit pas le marché cible de KivuFoot.

La ligne de contact extraite de cette pièce est exactement :

- nom : `Yves Bukasa` ;
- email : `yb752129@gmail.com` ;
- appels : `+257 64504091` ;
- WhatsApp : `+243 983753771`.

Cette pièce est la source confirmée utilisée par la configuration PDF. L'email
n'est donc pas repris simplement parce qu'il existe dans le bootstrap technique.
Le générateur utilise maintenant la mise en page PDF version 2 : une nouvelle
version est créée lorsque l'ancien document possède la même empreinte de
match, sans modifier les données sportives ni les historiques. Les variables
correspondantes sont :

```text
PDF_LOGO_PATH=
PDF_CONTACT_NAME=Yves Bukasa
PDF_CONTACT_EMAIL=yb752129@gmail.com
PDF_CONTACT_PHONE=+257 64504091
PDF_CONTACT_WHATSAPP=+243 983753771
```

Elles restent surchargeables par l'environnement uniquement après une nouvelle
validation publique. Une statistique absente reste `Non disponible` ; elle ne
doit jamais être remplacée par zéro.
