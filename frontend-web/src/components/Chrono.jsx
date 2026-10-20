import { useEffect, useState } from "react";
import { clockFromMatch, elapsed, formatClock, formatClockMinute, serverNow } from "../display.js";

export { elapsed };

export default function Chrono({
  match,
  startedAt,
  endedAt,
  running,
  periode,
  periodeStartedAt,
  pausedAt,
  precision = "second",
  as = "p",
  className = "chrono",
}) {
  const [now, setNow] = useState(serverNow());
  useEffect(() => {
    if (!running) return undefined;
    const t = setInterval(() => setNow(serverNow()), 1000);
    return () => clearInterval(t);
  }, [running]);

  const source = match || {
    started_at: startedAt,
    ended_at: endedAt,
    periode,
    periode_started_at: periodeStartedAt,
    paused_at: pausedAt,
  };
  if (!source.started_at) return null;
  if (source.periode === "mi_temps") return null;
  const freezeAt = source.ended_at || endedAt;
  const clock = clockFromMatch(
    source,
    running ? now : freezeAt ? new Date(freezeAt).getTime() : serverNow(),
  );
  const Element = as;
  const minuteAdditionnelle = source.minute_additionnelle ?? source.temps_additionnel ?? 0;
  const affichage = precision === "minute"
    ? formatClockMinute(clock.min, clock.sec, clock.periode, minuteAdditionnelle)
    : formatClock(clock.min, clock.sec, clock.periode);
  return <Element className={className}>{affichage}</Element>;
}


export function LiveMinute({ match, className = "live-minute" }) {
  if (!match?.started_at) return null;
  if (match.periode === "mi_temps") return <span className={className}>MT</span>;
  return (
    <Chrono
      precision="minute"
      as="span"
      className={className}
      match={match}
      running={match.statut === "en_cours" && !match.ended_at}
    />
  );
}
