import { useEffect, useState } from "react";

const STORAGE_KEY = "kivufoot_actualites_lues_v1";
const READ_EVENT = "kivufoot:actualites-read";

function normaliserIds(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((id) => Number(id))
    .filter((id) => Number.isInteger(id) && id > 0);
}

export function getActualitesLues() {
  if (typeof window === "undefined") return new Set();
  try {
    return new Set(normaliserIds(JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]")));
  } catch {
    return new Set();
  }
}

export function marquerActualiteLue(actualiteId) {
  const id = Number(actualiteId);
  if (!Number.isInteger(id) || id <= 0 || typeof window === "undefined") return;
  const lues = getActualitesLues();
  if (lues.has(id)) return;
  lues.add(id);
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...lues]));
    window.dispatchEvent(new Event(READ_EVENT));
  } catch {
    // Le badge reste fonctionnel même si le stockage local est indisponible.
  }
}

export function useActualitesLues() {
  const [, actualiser] = useState(0);

  useEffect(() => {
    const onChange = () => actualiser((version) => version + 1);
    window.addEventListener(READ_EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(READ_EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  return getActualitesLues();
}
