import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

function appareilIOS() {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent)
    || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

function dejaInstallee() {
  if (typeof window === "undefined") return false;
  return window.matchMedia?.("(display-mode: standalone)").matches
    || window.navigator.standalone === true
    || document.referrer.startsWith("android-app://");
}

export default function Installation() {
  const [installationEvent, setInstallationEvent] = useState(null);
  const [installee, setInstallee] = useState(dejaInstallee);
  const [message, setMessage] = useState("");
  const [erreur, setErreur] = useState("");
  const ios = useMemo(appareilIOS, []);

  useEffect(() => {
    function onBeforeInstallPrompt(event) {
      event.preventDefault();
      setInstallationEvent(event);
    }

    function onInstalled() {
      setInstallationEvent(null);
      setInstallee(true);
      setMessage("KivuFoot est maintenant installé sur cet appareil.");
    }

    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  async function installer() {
    setErreur("");
    setMessage("");

    if (installee) {
      setMessage("KivuFoot est déjà installé. Ouvrez-le depuis votre écran d’accueil ou vos applications.");
      return;
    }

    if (!installationEvent) {
      setMessage(
        ios
          ? "Sur iPhone ou iPad, utilisez le bouton Partager, puis choisissez « Ajouter à l’écran d’accueil »."
          : "L’installation directe n’est pas proposée par ce navigateur pour le moment. Suivez les étapes ci-dessous ou ouvrez cette page avec Chrome ou Edge."
      );
      return;
    }

    try {
      await installationEvent.prompt();
      const choix = await installationEvent.userChoice;
      setInstallationEvent(null);
      if (choix?.outcome === "accepted") {
        setMessage("Installation lancée. KivuFoot sera disponible sur votre écran d’accueil ou dans vos applications.");
      } else {
        setMessage("Installation annulée. Vous pourrez réessayer quand vous le souhaitez.");
      }
    } catch (error) {
      setErreur("Impossible d’ouvrir la fenêtre d’installation. Utilisez les instructions ci-dessous.");
      setInstallationEvent(null);
    }
  }

  const bouton = installee
    ? "KivuFoot est déjà installé"
    : installationEvent
      ? "Installer KivuFoot"
      : "Comment installer KivuFoot";

  return (
    <main className="install-page">
      <Link to="/" className="install-retour">← Retour à KivuFoot</Link>
      <section className="install-intro" aria-labelledby="installation-titre">
        <img className="install-logo" src="/icone-192.png" alt="" width="96" height="96" />
        <p className="kicker">Accès rapide</p>
        <h1 id="installation-titre">Installer KivuFoot</h1>
        <p>
          Ajoutez KivuFoot à votre écran d’accueil pour le retrouver facilement,
          comme une application. Il n’y a pas d’APK à télécharger : KivuFoot
          s’installe depuis cette page web.
        </p>
      </section>

      <button className="btn btn-primary install-action" type="button" onClick={installer}>
        {bouton}
      </button>

      {message && <p className="install-message" role="status">{message}</p>}
      {erreur && <p className="erreur" role="alert">{erreur}</p>}

      <section className="install-instructions" aria-labelledby="installation-etapes">
        <div className="section-head">
          <h2 id="installation-etapes">Selon votre appareil</h2>
        </div>
        <article className="install-step">
          <strong>Android / Chrome</strong>
          <p>
            Appuyez sur <b>Installer KivuFoot</b> si la fenêtre apparaît. Sinon,
            ouvrez le menu ⋮ de Chrome puis choisissez <b>Installer l’application</b>
            ou <b>Ajouter à l’écran d’accueil</b>.
          </p>
        </article>
        <article className="install-step">
          <strong>Ordinateur</strong>
          <p>
            Dans Chrome ou Edge, recherchez l’icône d’installation dans la barre
            d’adresse ou ouvrez le menu du navigateur, puis choisissez
            <b> Installer KivuFoot</b>.
          </p>
        </article>
        <article className="install-step">
          <strong>iPhone / iPad</strong>
          <p>
            Dans Safari, appuyez sur <b>Partager</b>, puis sur
            <b> Ajouter à l’écran d’accueil</b> et confirmez avec <b>Ajouter</b>.
          </p>
        </article>
      </section>

      <p className="install-note">
        L’installation dépend du navigateur. Si le bouton n’ouvre pas de fenêtre,
        les instructions ci-dessus indiquent la méthode disponible sur votre appareil.
      </p>
    </main>
  );
}
