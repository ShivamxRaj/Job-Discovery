"use client";

import { useEffect, useState } from "react";
import { Bell, BellRing, Check, Info } from "lucide-react";
import api from "@/lib/api";

export default function Notifications() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const data: any = await api.get("/notifications");
      setNotifications(data);
    } catch (err) {
      console.error("Failed to load notifications", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleRead = async (id: number) => {
    try {
      await api.post(`/notifications/${id}/read`, {});
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, is_read: true } : n)
      );
    } catch (err) {
      console.error("Failed to mark read", err);
    }
  };

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Loading Notifications...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Notifications</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Stay updated on daily matching crawls, new jobs indexed, and interview schedules.
        </p>
      </div>

      {notifications.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/20 p-12 text-center text-zinc-500">
          No notifications found.
        </div>
      ) : (
        <div className="space-y-4 max-w-4xl">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`rounded-2xl border p-4 flex gap-4 items-start justify-between transition-all ${
                n.is_read
                  ? "border-zinc-850 bg-zinc-950/40 opacity-70"
                  : "border-indigo-500/30 bg-indigo-950/5 shadow-[0_0_15px_rgba(79,70,229,0.05)]"
              }`}
            >
              <div className="flex gap-3 items-start">
                <div className={`rounded-lg p-2 ${n.is_read ? "bg-zinc-900 text-zinc-500" : "bg-indigo-950 text-indigo-400"}`}>
                  <BellRing className="h-4.5 w-4.5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">{n.title}</h4>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">{n.content}</p>
                  <span className="text-[10px] text-zinc-550 block mt-2">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {!n.is_read && (
                <button
                  onClick={() => handleRead(n.id)}
                  className="rounded border border-zinc-800 bg-zinc-900 p-1 hover:bg-zinc-800 hover:text-white transition-colors"
                >
                  <Check className="h-4.5 w-4.5 text-zinc-400" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
