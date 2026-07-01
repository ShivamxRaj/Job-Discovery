"use client";

import { useEffect, useState } from "react";
import { Shield, Users, RefreshCw, BarChart2, Activity, Play } from "lucide-react";
import api from "@/lib/api";

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [usersList, setUsersList] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState("");

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const s = await api.get("/admin/stats");
      const l: any = await api.get("/admin/audit-logs").catch(() => []);
      const u: any = await api.get("/admin/users").catch(() => []);
      setStats(s);
      setLogs(l);
      setUsersList(u);
    } catch (err) {
      console.error("Failed to load admin stats", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const triggerIngest = async () => {
    setIngesting(true);
    setIngestMsg("");
    try {
      const res: any = await api.post("/jobs/trigger-ingestion", {});
      setIngestMsg(res.message || "Ingestion complete!");
      // Reload stats
      const s = await api.get("/admin/stats");
      setStats(s);
    } catch (err: any) {
      setIngestMsg(err.message || "Failed to trigger ingestion.");
    } finally {
      setIngesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Accessing Admin Portal...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-zinc-900 pb-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Shield className="h-8 w-8 text-indigo-500" />
            Admin Dashboard
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            System administration console: oversee scrapers, check audit trails, and review system usage metrics.
          </p>
        </div>

        <button
          onClick={triggerIngest}
          disabled={ingesting}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors shrink-0"
        >
          <Play className="h-4 w-4" />
          {ingesting ? "Ingesting..." : "Ingest Jobs from APIs"}
        </button>
      </div>

      {ingestMsg && (
        <div className="rounded-lg bg-indigo-950/40 border border-indigo-900/60 p-3 text-xs text-indigo-400">
          {ingestMsg}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <div className="flex justify-between items-start text-zinc-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Total Users</span>
              <Users className="h-4.5 w-4.5 text-indigo-400" />
            </div>
            <p className="mt-2 text-3xl font-black text-white">{stats.total_users}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <div className="flex justify-between items-start text-zinc-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Indexed Jobs</span>
              <BarChart2 className="h-4.5 w-4.5 text-emerald-400" />
            </div>
            <p className="mt-2 text-3xl font-black text-white">{stats.total_jobs}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <div className="flex justify-between items-start text-zinc-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Parsed Resumes</span>
              <Activity className="h-4.5 w-4.5 text-blue-400" />
            </div>
            <p className="mt-2 text-3xl font-black text-white">{stats.total_resumes}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <div className="flex justify-between items-start text-zinc-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Tracked Applications</span>
              <RefreshCw className="h-4.5 w-4.5 text-purple-400" />
            </div>
            <p className="mt-2 text-3xl font-black text-white">{stats.total_applications}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* User list */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 space-y-4">
          <h3 className="text-base font-bold text-white uppercase tracking-wider text-zinc-400">
            Registered Users
          </h3>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {usersList.map((u) => (
              <div key={u.id} className="flex justify-between items-center rounded-xl bg-zinc-900/30 p-3 border border-zinc-850">
                <span className="text-xs font-medium text-white">{u.email}</span>
                <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                  u.is_superuser ? "bg-red-950/40 border border-red-900/60 text-red-400" : "bg-zinc-900 border border-zinc-800 text-zinc-400"
                }`}>
                  {u.is_superuser ? "Admin" : "Candidate"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Audit Logs */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 space-y-4">
          <h3 className="text-base font-bold text-white uppercase tracking-wider text-zinc-400">
            System Audit Trail
          </h3>
          <div className="space-y-3 max-h-80 overflow-y-auto font-mono text-[10px] text-zinc-400">
            {logs.map((log) => (
              <div key={log.id} className="border-b border-zinc-900 pb-2">
                <div className="flex justify-between items-center text-zinc-550">
                  <span>Action: {log.action}</span>
                  <span>{new Date(log.created_at).toLocaleTimeString()}</span>
                </div>
                <p className="text-zinc-300 mt-1">IP: {log.ip_address || "Internal"} &bull; Agent: {log.user_agent || "System"}</p>
              </div>
            ))}

            {logs.length === 0 && (
              <div className="text-center py-10 text-zinc-650">No audit logs stored yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
