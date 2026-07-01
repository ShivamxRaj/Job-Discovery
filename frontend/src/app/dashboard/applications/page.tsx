"use client";

import { useEffect, useState } from "react";
import { Kanban, ChevronRight, ChevronLeft, Calendar, FileText, CheckCircle2 } from "lucide-react";
import api from "@/lib/api";

export default function Applications() {
  const [apps, setApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchApps = async () => {
    setLoading(true);
    try {
      const data: any = await api.get("/applications");
      setApps(data);
    } catch (err) {
      console.error("Failed to load applications", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApps();
  }, []);

  const columns = [
    { name: "Applied", color: "bg-zinc-900 border-zinc-800" },
    { name: "Interview", color: "bg-indigo-950/20 border-indigo-900/60" },
    { name: "Rejected", color: "bg-red-950/20 border-red-900/40" },
    { name: "Offer", color: "bg-emerald-950/20 border-emerald-900/40" }
  ];

  const moveStage = async (appId: number, currentStatus: string, direction: "next" | "prev") => {
    const statuses = ["Applied", "Interview", "Rejected", "Offer"];
    const idx = statuses.indexOf(currentStatus);
    let nextIdx = idx;
    
    if (direction === "next" && idx < statuses.length - 1) {
      nextIdx = idx + 1;
    } else if (direction === "prev" && idx > 0) {
      nextIdx = idx - 1;
    }

    if (nextIdx === idx) return;
    const newStatus = statuses[nextIdx];

    try {
      await api.put(`/applications/${appId}`, { status: newStatus });
      setApps(prev => prev.map(a => a.id === appId ? { ...a, status: newStatus } : a));
    } catch (err) {
      console.error("Failed to update status", err);
    }
  };

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Loading Kanban Pipeline...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Application Kanban</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Track interview progression, rejected applications, and job offers in your funnel.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {columns.map((col) => {
          const colApps = apps.filter(a => a.status === col.name);
          return (
            <div key={col.name} className={`rounded-2xl border p-4 flex flex-col min-h-[60vh] ${col.color}`}>
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-4">
                <span className="text-sm font-bold text-white uppercase tracking-wider">{col.name}</span>
                <span className="rounded-full bg-zinc-900 border border-zinc-800 px-2 py-0.5 text-xs text-zinc-400 font-semibold">
                  {colApps.length}
                </span>
              </div>

              <div className="flex-1 space-y-3 overflow-y-auto">
                {colApps.map((app) => (
                  <div key={app.id} className="rounded-xl border border-zinc-800 bg-black p-4 space-y-3 relative group">
                    <div>
                      <h4 className="text-sm font-bold text-white">{app.job.title}</h4>
                      <p className="text-xs text-zinc-500 mt-0.5">{app.job.company.name}</p>
                    </div>

                    <div className="flex items-center gap-1 text-[10px] text-zinc-500">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>{new Date(app.created_at).toLocaleDateString()}</span>
                    </div>

                    {/* Progress shifting controls */}
                    <div className="flex justify-between items-center border-t border-zinc-900 pt-3">
                      <button
                        onClick={() => moveStage(app.id, app.status, "prev")}
                        className="rounded p-1 border border-zinc-850 hover:bg-zinc-900 text-zinc-500 hover:text-white transition-colors"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <span className="text-[10px] font-semibold text-zinc-600">Stage Shift</span>
                      <button
                        onClick={() => moveStage(app.id, app.status, "next")}
                        className="rounded p-1 border border-zinc-850 hover:bg-zinc-900 text-zinc-500 hover:text-white transition-colors"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}

                {colApps.length === 0 && (
                  <div className="h-full flex items-center justify-center text-zinc-600 text-xs py-10 border border-dashed border-zinc-900 rounded-xl">
                    No applications here.
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
