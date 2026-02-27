// ======================================
// VoiceSafe Global Config
// Production + Local + Future Scaling
// ======================================

(function () {

  const host = window.location.hostname;

  // -----------------------------
  // ENV DETECTION
  // -----------------------------
  const ENV =
    (host === "localhost" || host === "127.0.0.1")
      ? "LOCAL"
      : (host.includes("staging") || host.includes("preview"))
        ? "STAGING"
        : "PROD";

  // -----------------------------
  // API ENDPOINTS
  // -----------------------------
  const API_ENDPOINTS = {

    LOCAL: "http://127.0.0.1:10000",

    // future staging (optional)
    STAGING: "https://voicesafe-backend-staging.onrender.com",

    // production backend
    PROD: "https://voicesafe-backend-1.onrender.com"
  };

  // -----------------------------
  // GLOBAL CONFIG OBJECT
  // -----------------------------
  window.VOICE_SAFE_CONFIG = {

    ENV,

    API_BASE: API_ENDPOINTS[ENV],

    VERSION: "2026.03.enterprise",

    DEBUG: ENV !== "PROD",

    FEATURES: {
      DEMO_MODE: true,
      AUTO_SCROLL_RESULTS: true,
      TOASTS: true,
      ANALYTICS_READY: true
    }
  };

  // legacy compatibility
  window.API_BASE = window.VOICE_SAFE_CONFIG.API_BASE;

  // -----------------------------
  // DEBUG LOG (dev only)
  // -----------------------------
  if (window.VOICE_SAFE_CONFIG.DEBUG) {
    console.log("VoiceSafe CONFIG");
    console.log("ENV:", ENV);
    console.log("API:", window.API_BASE);
  }

})();