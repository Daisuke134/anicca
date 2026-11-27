// Drop-in config. Placeholder values keep the app in offline demo mode.
// Env vars (see .env.example) override any non-empty field at build time.
// Do not put a registered App Check debug token in this committed file.
window.__HYBRID_AFFIRMATIONS_CONFIG__ = {
  apiKey: "YOUR_FIREBASE_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.firebasestorage.app",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_FIREBASE_APP_ID",
  appCheckSiteKey: "YOUR_RECAPTCHA_V3_SITE_KEY",
  appCheckDebugToken: "",
};
