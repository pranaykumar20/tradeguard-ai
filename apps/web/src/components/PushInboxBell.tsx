"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getPushConfig,
  getPushInbox,
  markAllPushRead,
  markPushRead,
  subscribePush,
  type PushNotification,
} from "@/lib/api";

const POLL_MS = 30_000;

function severityClass(severity: string) {
  if (severity === "high") return "border-red/40 bg-red/10";
  if (severity === "low") return "border-card-border";
  return "border-orange/40 bg-orange/10";
}

export function PushInboxBell() {
  const [open, setOpen] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [vapidKey, setVapidKey] = useState<string | null>(null);
  const [items, setItems] = useState<PushNotification[]>([]);
  const [unread, setUnread] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const data = await getPushInbox(20);
      setItems(data.notifications);
      setUnread(data.unread);
    } catch {
      // inbox optional when API offline
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const cfg = await getPushConfig();
        if (cancelled) return;
        setEnabled(cfg.enabled);
        setVapidKey(cfg.vapid_public_key);
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [enabled, refresh]);

  async function handleSubscribe() {
    if (!vapidKey || !("serviceWorker" in navigator) || !("PushManager" in window)) return;
    try {
      const reg = await navigator.serviceWorker.register("/sw.js");
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      });
      await subscribePush(sub.toJSON() as { endpoint: string; keys?: Record<string, string> });
    } catch {
      // mock mode — inbox still works
    }
  }

  async function handleOpen() {
    const next = !open;
    setOpen(next);
    if (next && unread > 0) {
      await markAllPushRead();
      setUnread(0);
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
    }
  }

  async function handleMarkRead(id: string) {
    await markPushRead(id);
    await refresh();
  }

  if (!enabled) return null;

  return (
    <div className="relative mb-3">
      <button
        type="button"
        onClick={() => void handleOpen()}
        className="flex w-full items-center justify-between rounded-[14px] border border-card-border px-3 py-2 text-xs font-bold transition hover:border-teal/40"
        aria-label="Notifications"
      >
        <span>Alerts</span>
        {unread > 0 && (
          <span className="rounded-full bg-teal px-2 py-0.5 text-[10px] text-background">{unread}</span>
        )}
      </button>

      {open && (
        <div className="absolute bottom-full left-0 z-50 mb-2 w-full max-h-[280px] overflow-y-auto rounded-[14px] border border-card-border bg-[#07111f] p-2 shadow-xl">
          {vapidKey && (
            <button
              type="button"
              onClick={() => void handleSubscribe()}
              className="mb-2 w-full rounded-lg border border-teal/30 px-2 py-1 text-[10px] font-bold text-teal"
            >
              Enable browser push
            </button>
          )}
          {items.length === 0 && (
            <p className="px-2 py-3 text-xs text-muted">No notifications yet.</p>
          )}
          {items.map((note) => (
            <button
              key={note.id}
              type="button"
              onClick={() => void handleMarkRead(note.id)}
              className={`mb-1 w-full rounded-lg border p-2 text-left text-xs ${severityClass(note.severity)} ${
                note.read ? "opacity-60" : ""
              }`}
            >
              <div className="font-bold">{note.title}</div>
              <div className="tg-sub mt-0.5 line-clamp-2">{note.body}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}
