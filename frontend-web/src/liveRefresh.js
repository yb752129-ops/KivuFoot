export function startVisibleRefresh(load, intervalMs = 10000) {
  let stopped = false;
  let running = false;
  let timer = null;

  function clearTimer() {
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  function schedule() {
    clearTimer();
    if (stopped || document.hidden) return;
    timer = window.setTimeout(run, intervalMs);
  }

  async function run() {
    if (stopped || document.hidden || running) return;
    running = true;
    try {
      await load();
    } catch {
      // The page keeps its last good public snapshot during a transient outage.
    } finally {
      running = false;
      schedule();
    }
  }

  function onVisibilityChange() {
    clearTimer();
    if (!document.hidden) run();
  }

  document.addEventListener("visibilitychange", onVisibilityChange);
  run();
  return () => {
    stopped = true;
    clearTimer();
    document.removeEventListener("visibilitychange", onVisibilityChange);
  };
}
