/* TradeGuard — minimal service worker for web push (Phase 9) */
self.addEventListener("push", (event) => {
  let data = { title: "TradeGuard", body: "New alert" };
  try {
    if (event.data) data = event.data.json();
  } catch {
    // ignore malformed payload
  }
  event.waitUntil(
    self.registration.showNotification(data.title || "TradeGuard", {
      body: data.body || "",
      icon: "/favicon.ico",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow("/approvals"));
});
