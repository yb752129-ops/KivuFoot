import { useEffect, useState } from "react";
import { clockFromMatch, elapsed, formatClock } from "../display.js";

export { elapsed };

export default function Chrono({ match, startedAt, endedAt, running, periode, periodeStartedAt, pausedAt }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!running) return undefined;
    const t = setInterval(() => setNow(Date.now()), 1000);
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
  const clock = clockFromMatch(source, running ? now : endedAt ? new Date(endedAt).getTime() : now);
  return <p className="chrono">{formatClock(clock.min, clock.sec, clock.periode)}</p>;
}
