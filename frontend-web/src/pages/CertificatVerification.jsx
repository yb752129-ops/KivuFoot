import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { certificatsAPI } from '../api.js';
import './certificat.css';

export default function CertificatVerification() {
  const {code} = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let active = true;
    setData(null); setError(null);
    certificatsAPI.verifier(code).then(d => {if(active) setData(d);}).catch(e => {if(active) setError(e);});
    return () => {active = false;};
  }, [code]);
  return <main className="cert-check"><div className="cert-wrap">
    <div className="cert-top"><Link to="/" className="cert-brand">KIVU<span>FOOT</span></Link><span>REGISTRE DES DISTINCTIONS</span></div>
    <section className="cert-card" aria-live="polite">
      <div className="cert-label">VÉRIFICATION DU CERTIFICAT</div>
      {!data && !error && <h1>Vérification en cours…</h1>}
      {error && <><div className="cert-badge cert-warn">Vérification impossible</div><h1>{error.status === 404 ? 'Certificat introuvable' : 'Service indisponible'}</h1><p>{error.status === 404 ? 'Cet identifiant ne correspond à aucun certificat enregistré.' : 'La connexion au registre a échoué. Réessayez plus tard.'}</p></>}
      {data && <><div className={'cert-badge ' + (data.statut === 'actif' ? 'cert-ok' : 'cert-warn')}>{data.statut === 'actif' ? '✓ CERTIFICAT AUTHENTIQUE' : '✕ CERTIFICAT ANNULÉ'}</div>
      <h1>{data.laureat}</h1><p className="cert-intro">{data.statut === 'actif' ? 'Distinction enregistrée dans le registre KivuFoot.' : 'Cette distinction a été annulée dans le registre KivuFoot.'}</p>
      <dl className="cert-details"><div><dt>Distinction</dt><dd>{data.distinction}</dd></div><div><dt>Équipe</dt><dd>{data.equipe}</dd></div><div><dt>Compétition</dt><dd>{data.tournoi}</dd></div><div><dt>Organisateur</dt><dd>{data.organisateur}</dd></div><div><dt>Référence</dt><dd className="cert-code">{data.code}</dd></div></dl>
      <div className="cert-notice">Comparez ces informations avec le certificat présenté. Un QR code peut être copié ; cette page confirme uniquement le statut de l’enregistrement.</div></>}
    </section><p className="cert-footer">KivuFoot · Vérification des distinctions</p>
  </div></main>;
}
