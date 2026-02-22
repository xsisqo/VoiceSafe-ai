// config.js
window.API_BASE =
  (location.hostname === "127.0.0.1" || location.hostname === "localhost")
    ? "http://127.0.0.1:10000"
    : "https://voicesafe-backend-1.onrender.com";