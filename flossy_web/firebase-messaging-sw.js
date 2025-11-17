// ✅ Firebase Messaging Service Worker (root folder, same level as index.html)
importScripts("https://www.gstatic.com/firebasejs/11.0.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/11.0.1/firebase-messaging-compat.js");

// 🔧 Initialize Firebase inside the service worker
firebase.initializeApp({
  apiKey: "AIzaSyCusU0d_qu4hr-k1xKXmQtTpVXpShCcOGI",
  authDomain: "flossy-62a22.firebaseapp.com",
  projectId: "flossy-62a22",
  storageBucket: "flossy-62a22.firebasestorage.app",
  messagingSenderId: "620594247395",
  appId: "1:620594247395:web:02f0ec4be8e884359cb7d6",
  measurementId: "G-8NB5F8N12M",
});

// ✅ Initialize Firebase Messaging
const messaging = firebase.messaging();

// ===============================
// 💬 Handle Background Messages
// ===============================
messaging.onBackgroundMessage((payload) => {
  console.log("📨 Received background message:", payload);

  // Safely extract notification details
  const notification = payload.notification || {};
  const data = payload.data || {};

  const notificationTitle = notification.title || data.title || "FlossyAI Notification";
  const notificationOptions = {
    body: notification.body || data.body || "You have a new message from FlossyAI!",
    icon: notification.icon || data.icon || "/static/flossy-icon.png", // optional
    badge: data.badge || "/static/flossy-badge.png", // optional
    data: {
      url: data.url || "/", // where to navigate when user clicks
    },
  };

  // Show notification
  self.registration.showNotification(notificationTitle, notificationOptions);
});

// ===============================
// 🚀 Handle Clicks on Notifications
// ===============================
self.addEventListener("notificationclick", function (event) {
  console.log("🖱️ Notification click received:", event);
  event.notification.close();

  // Focus existing tab or open a new one
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((clientList) => {
      for (const client of clientList) {
        if ("focus" in client) {
          if (event.notification.data && event.notification.data.url) {
            client.navigate(event.notification.data.url);
          }
          return client.focus();
        }
      }
      if (clients.openWindow && event.notification.data && event.notification.data.url) {
        return clients.openWindow(event.notification.data.url);
      }
    })
  );
});

// ===============================
// 🧹 Optional: Handle SW Activation
// ===============================
self.addEventListener("activate", (event) => {
  console.log("🔥 Firebase messaging service worker activated");
});
