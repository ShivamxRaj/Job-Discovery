"use client";

import { useEffect, useState } from "react";
import { Sparkles, Bookmark, Trash2, CheckCircle, ExternalLink } from "lucide-react";
import api from "@/lib/api";

export default function SavedJobs() {
  const [savedJobs, setSavedJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSaved = async () => {
    setLoading(true);
    try {
      const data: any = await api.get("/jobs/recommendations");
      // filter only is_saved = true
      const filtered = data.filter((r: any) => r.is_saved === true);
      setSavedJobs(filtered);
    } catch (err) {
      console.error("Failed to load saved jobs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSaved();
  }, []);

  const handleRemove = async (jobId: number) => {
    try {
      // In our simple API, saving again toggle off or dismiss works.
      // We can mock removing bookmark or calling dismiss.
      await api.post(`/jobs/recommendations/${jobId}/dismiss`, {});
      setSavedJobs(prev => prev.filter(r => r.job_id !== jobId));
    } catch (err) {
      console.error("Failed to remove saved job", err);
    }
  };

  const handleLogApplication = async (jobId: number, resumeVerId: number) => {
    try {
      await api.post("/applications", {
        job_id: jobId,
        resume_version_id: resumeVerId,
        status: "Applied"
      });
      alert("Application logged.");
    } catch (err: any) {
      alert(err.message || "Failed to log application.");
    }
  };

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Loading Bookmarked Jobs...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Saved Jobs</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Your bookmarked positions. Quick-access applications or generate outreach resources here.
        </p>
      </div>

      {savedJobs.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/20 p-12 text-center text-zinc-500">
          No saved jobs bookmarked yet.
        </div>
      ) : (
        <div className="space-y-6">
          {savedJobs.map((rec) => (
            <div key={rec.id} className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 flex flex-col gap-4">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-lg font-bold text-white">{rec.job.title}</h3>
                    <span className="rounded-full bg-indigo-950 border border-indigo-900 px-2 py-0.5 text-xs font-semibold text-indigo-400 flex items-center gap-1">
                      <Sparkles className="h-3 w-3" />
                      {rec.score}% Match
                    </span>
                  </div>
                  <p className="text-sm text-zinc-400 mt-1">
                    {rec.job.company.name} &bull; {rec.job.location} &bull; {rec.job.job_type}
                  </p>
                </div>

                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => handleRemove(rec.job_id)}
                    className="flex items-center gap-1.5 rounded-lg border border-zinc-850 bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-zinc-400 hover:text-red-400 transition-all"
                  >
                    <Trash2 className="h-4 w-4" />
                    Unsave
                  </button>
                  <button
                    onClick={() => handleLogApplication(rec.job_id, rec.resume_version_id)}
                    className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition-all"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Track Apply
                  </button>
                </div>
              </div>

              <p className="text-xs text-zinc-500 max-w-4xl line-clamp-2">
                {rec.job.description}
              </p>

              <div className="flex border-t border-zinc-900 pt-4 mt-1 text-xs text-zinc-500">
                <a
                  href={rec.job.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  Apply Directly
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
