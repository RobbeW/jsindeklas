/* Timed assessment configuration and exclusive, durable attempt storage. */
(function () {
  "use strict";

  function validIdentifier(value) {
    return typeof value === "string" && /^[A-Za-z0-9_-]+$/.test(value);
  }

  function validConfig(config) {
    return config && validIdentifier(config.id) && validIdentifier(config.contentRevision) &&
      (config.kind === "test" || config.kind === "exam") &&
      Number.isInteger(config.durationMinutes) && config.durationMinutes > 0 &&
      config.durationMinutes <= (config.kind === "exam" ? 100 : 45);
  }

  async function loadConfig(id) {
    if (!validIdentifier(id)) throw new Error("Ongeldige evaluatie.");
    let manifest;
    try {
      const response = await fetch("evaluaties/assessments.json", { cache: "no-store", credentials: "same-origin" });
      if (!response.ok) throw new Error("manifest unavailable");
      manifest = await response.json();
    } catch (_) {
      throw new Error("De evaluatie-instellingen konden niet worden geladen. Probeer opnieuw.");
    }
    const matches = Array.isArray(manifest?.assessments) ? manifest.assessments.filter(item => item && item.id === id) : [];
    if (matches.length !== 1 || !validConfig(matches[0])) {
      throw new Error("De evaluatie-instellingen zijn ongeldig. Vraag hulp aan je leerkracht.");
    }
    return matches[0];
  }

  function validState(state) {
    const isRecord = value => Boolean(value && typeof value === "object" && !Array.isArray(value));
    if (!isRecord(state) || typeof state.attemptId !== "string" || !state.attemptId.trim() ||
        typeof state.name !== "string" || typeof state.className !== "string" ||
        !Number.isFinite(state.startedAt) || !Number.isFinite(state.deadline) || state.deadline <= state.startedAt) {
      return false;
    }
    if (state.final === null) return isRecord(state.drafts) && isRecord(state.runs);
    return isRecord(state.final) && Number.isFinite(state.final.finishedAt) &&
      (state.final.reason === "manual" || state.final.reason === "expiry") &&
      Array.isArray(state.final.records) && state.final.records.every(isRecord);
  }

  async function open(config) {
    if (!validConfig(config)) throw new Error("De evaluatie-instellingen zijn ongeldig.");
    if (!navigator.locks || typeof navigator.locks.request !== "function") {
      throw new Error("Deze browser kan je evaluatie niet veilig vergrendelen. Vraag hulp aan je leerkracht.");
    }
    const key = `jsik-attempt:${config.id}:${config.contentRevision}`;
    let unlock;
    const held = new Promise(resolve => { unlock = resolve; });
    let settle;
    const acquired = new Promise(resolve => { settle = resolve; });
    let active = true;
    function release() {
      if (!active) return;
      active = false;
      window.removeEventListener("pagehide", release);
      unlock();
    }
    window.addEventListener("pagehide", release);
    let request;
    try {
      request = navigator.locks.request(`jsik-attempt:${config.id}`, { ifAvailable: true }, async lock => {
        settle(!!lock);
        if (lock) await held;
      });
      request.catch(() => settle(false));
    } catch (_) {
      release();
      throw new Error("De evaluatie kon niet veilig worden vergrendeld. Probeer opnieuw.");
    }
    if (!await acquired || !active) {
      release();
      throw new Error("Deze evaluatie is al open in een ander tabblad of kan niet worden vergrendeld.");
    }
    let state;
    try {
      const raw = localStorage.getItem(key);
      state = raw === null ? null : JSON.parse(raw);
      if (raw === null) {
        const probe = `${key}:probe:${Math.random().toString(36).slice(2)}`;
        localStorage.setItem(probe, "1");
        if (localStorage.getItem(probe) !== "1") throw new Error("storage unavailable");
        localStorage.removeItem(probe);
      } else if (!validState(state)) {
        throw new Error("invalid state");
      }
    } catch (_) {
      release();
      throw new Error("Je opgeslagen evaluatie is beschadigd of opslag is niet beschikbaar. Vraag hulp aan je leerkracht.");
    }
    return {
      get state() { return state === null ? null : JSON.parse(JSON.stringify(state)); },
      commit(nextState) {
        if (!active || !validState(nextState)) return false;
        try {
          const serialized = JSON.stringify(nextState);
          const copy = JSON.parse(serialized);
          if (!validState(copy)) return false;
          localStorage.setItem(key, serialized);
          if (localStorage.getItem(key) !== serialized) return false;
          state = copy;
          return true;
        } catch (_) { return false; }
      },
      release,
    };
  }

  window.addEventListener("pageshow", event => { if (event.persisted) window.location.reload(); });
  window.JSIKTimedAttempt = { loadConfig, open };
})();
