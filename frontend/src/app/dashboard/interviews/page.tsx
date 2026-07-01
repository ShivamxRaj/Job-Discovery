"use client";

import { useEffect, useState } from "react";
import { CalendarDays, AlertCircle, HelpCircle, CheckCircle, Clock } from "lucide-react";
import api from "@/lib/api";

export default function Interviews() {
  const [interviews, setInterviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInterviews = async () => {
      try {
        const data: any = await api.get("/applications");
        const filtered = data.filter((a: any) => a.status === "Interview");
        setInterviews(filtered);
      } catch (err) {
        console.error("Failed to load interviews", err);
      } finally {
        setLoading(false);
      }
    };

    fetchInterviews();
  }, []);

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Loading Interviews...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Interview Tracker</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Track upcoming technical rounds, coding screens, and followups for roles in your interview pipeline.
        </p>
      </div>

      {interviews.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/20 p-12 text-center text-zinc-500">
          No interviews scheduled yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {interviews.map((item) => (
            <div key={item.id} className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-bold text-white">{item.job.title}</h3>
                  <p className="text-sm text-zinc-400">{item.job.company.name}</p>
                </div>
                <span className="rounded-full bg-indigo-950 border border-indigo-900 px-3 py-1 text-xs font-semibold text-indigo-400 flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  Interviewing
                </span>
              </div>

              <div className="rounded-xl border border-zinc-900 bg-black p-4 flex gap-3 text-xs text-zinc-300">
                <CalendarDays className="h-5 w-5 text-indigo-400 shrink-0" />
                <div>
                  <p className="font-semibold text-white">Location details</p>
                  <p className="text-zinc-500 mt-0.5">{item.job.location}</p>
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-semibold text-zinc-400">Interview Preparation Guidance:</span>
                <ul className="space-y-1 text-xs text-zinc-500">
                  <li>&bull; Practice matching skills: {item.job.skills?.map((s: any) => s.skill_name).join(", ")}.</li>
                  <li>&bull; Generate HR outreach template to verify round schedule.</li>
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
