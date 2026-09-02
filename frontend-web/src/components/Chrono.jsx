import { useEffect, useState } from "react";

export function elapsed(startedAt, endedAt, now = Date.now()) {
  if (!startedAt) return { min: 0, sec: 0 };
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : now;
  const ms = Math.max(0, end - start);
  return { min: Math.floor(ms / 60000), sec: Math.floor((ms % 60000) / 1000) };
}

export default function Chrono({ startedAt, endedAt, running }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!running) return undefined;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [running]);
  if (!startedAt) return null;
  const { min, sec } = elapsed(startedAt, running ? null : endedAt, now);
  return (
    <p className="chrono">
      {min}′{String(sec).padStart(2, "0")}″
    </p>
  );
}
