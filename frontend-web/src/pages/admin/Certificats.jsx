import {useEffect, useState} from 'react';
import {certificatsAPI} from '../../api.js';
const empty = {laureat:'', distinction:'', equipe:'', tournoi:'', organisateur:''};
export default function AdminCertificats(){
  const [form,setForm]=useState(empty),[items,setItems]=useState([]),[error,setError]=useState(''),[info,setInfo]=useState(''),[busy,setBusy]=useState(false),[approved,setApproved]=useState(false);
  async function reload(){try{setItems(await certificatsAPI.lister());}catch(e){setError(e.message);}}
  useEffect(()=>{reload();},[]);
  async function create(e){e.preventDefault();if(!approved || busy)return;setError('');setInfo('');setBusy(true);try{await certificatsAPI.creer(form);setForm(empty);setApproved(false);setInfo('Certificat enregistré. Vérifiez la page avant de créer le QR code.');await reload();}catch(err){setError(err.message);}finally{setBusy(false);}}
  async function cancel(item){const motif=window.prompt('Motif d’annulation (au moins 3 caractères) :');if(motif===null)return;if(motif.trim().length<3){setError('Motif trop court.');return;}if(!window.confirm(`Annuler le certificat de ${item.laureat} ? Le QR affichera alors « annulé ».`))return;setBusy(true);setError('');try{await certificatsAPI.annuler(item.code,motif);setInfo('Certificat annulé.');await reload();}catch(e){setError(e.message);}finally{setBusy(false);}}
  return <main style={{padding:'1.5rem 0 4rem',maxWidth:'720px'}}><h1>Certificats de distinction</h1><p>Enregistrez uniquement les distinctions approuvées par les organisateurs. La création est réservée à l’administrateur.</p>
  {error && <p role="alert">{error}</p>}{info && <p role="status">{info}</p>}
  <form onSubmit={create} style={{display:'grid',gap:12}}>{[['laureat','Nom complet du lauréat'],['distinction','Distinction'],['equipe','Équipe'],['tournoi','Tournoi et édition'],['organisateur','Organisateur']].map(([k,label])=><label key={k} className="field">{label}<input required maxLength={k==='tournoi'?250:200} value={form[k]} onChange={e=>setForm({...form,[k]:e.target.value})}/></label>)}
  <label><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)}/> Je confirme l’approbation des organisateurs et l’exactitude des informations.</label><button className="btn btn-primary" disabled={!approved||busy}>Enregistrer la distinction</button></form>
  <h2>Registre</h2><p>Les 200 dernières entrées.</p>{items.map(item=><article key={item.code} style={{borderTop:'1px solid #777',padding:'1rem 0',overflowWrap:'anywhere'}}><strong>{item.laureat}</strong> · {item.distinction}<p>Statut : {item.statut==='actif'?'actif':'annulé'}</p><p><a href={`/certificats/${item.code}`}>Ouvrir la page de vérification</a></p>{item.statut==='actif' && <button className="btn btn-danger" disabled={busy} onClick={()=>cancel(item)}>Annuler le certificat</button>}</article>)}
  </main>;
}
