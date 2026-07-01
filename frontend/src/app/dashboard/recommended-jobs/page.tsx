"use client";

import { useEffect, useState } from "react";
import { Sparkles, Bookmark, Eye, Mail, FileText, CheckCircle, ExternalLink, X } from "lucide-react";
import api from "@/lib/api";

export default function RecommendedJobs() {
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modal states
  const [activeJob, setActiveJob] = useState<any>(null);
  const [modalType, setModalType] = useState<"cover" | "email" | null>(null);
  const [modalText, setModalText] = useState("");
  const [generating, setGenerating] = useState(false);
  
  // Versions select
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVerId, setSelectedVerId] = useState<number | null>(null);

  const fetchRecs = async (verId?: number) => {
    setLoading(true);
    try {
      const url = verId ? `/jobs/recommendations?resume_version_id=${verId}` : "/jobs/recommendations";
      const data: any = await api.get(url);
      setRecommendations(data);
    } catch (err) {
      console.error("Failed to load recommendations", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const initData = async () => {
      try {
        const resumes: any = await api.get("/resumes");
        if (resumes.length > 0) {
          const vers: any = await api.get(`/resumes/${resumes[0].id}/versions`);
          setVersions(vers);
          if (vers.length > 0) {
            setSelectedVerId(vers[0].id);
            fetchRecs(vers[0].id);
            return;
          }
        }
        setLoading(false);
      } catch (err) {
        console.error("Failed to init resume list", err);
        setLoading(false);
      }
    };
    initData();
  }, []);

  const handleSave = async (jobId: number) => {
    try {
      await api.post(`/jobs/recommendations/${jobId}/save`, {});
      setRecommendations(prev =>
        prev.map(r => r.job_id === jobId ? { ...r, is_saved: true } : r)
      );
    } catch (err) {
      console.error("Failed to save job", err);
    }
  };

  const handleDismiss = async (jobId: number) => {
    try {
      await api.post(`/jobs/recommendations/${jobId}/dismiss`, {});
      setRecommendations(prev => prev.filter(r => r.job_id !== jobId));
    } catch (err) {
      console.error("Failed to dismiss job", err);
    }
  };

  const handleLogApplication = async (jobId: number) => {
    if (!selectedVerId) return;
    try {
      await api.post("/applications", {
        job_id: jobId,
        resume_version_id: selectedVerId,
        status: "Applied"
      });
      alert("Job added to application tracker.");
    } catch (err: any) {
      alert(err.message || "Failed to log application.");
    }
  };

  const generateOutreach = async (type: "cover" | "email", job: any) => {
    if (!selectedVerId) return;
    setActiveJob(job);
    setModalType(type);
    setGenerating(true);
    setModalText("");

    try {
      const endpoint = type === "cover" ? "/applications/generate-cover-letter" : "/applications/generate-hr-email";
      const res: any = await api.post(endpoint, {
        job_id: job.id,
        resume_version_id: selectedVerId
      });
      setModalText(type === "cover" ? res.cover_letter : res.hr_email);
    } catch (err: any) {
      setModalText("Failed to generate outreach resource. Check backend logs.");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Computing Vector Matches...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Recommended Jobs</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Top matches computed by vector distance and weighted preference overlays.
          </p>
        </div>

        {versions.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Matching Resume:</span>
            <select
              value={selectedVerId || ""}
              onChange={(e) => {
                const val = Number(e.target.value);
                setSelectedVerId(val);
                fetchRecs(val);
              }}
              className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs text-white focus:outline-none"
            >
              {versions.map((ver) => (
                <option key={ver.id} value={ver.id}>
                  Version {ver.version_number} (ATS: {ver.parsed_data?.ats_score}%)
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {recommendations.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/20 p-12 text-center">
          <p className="text-sm text-zinc-500">No recommended jobs matching your profile found.</p>
          <p className="text-xs text-zinc-600 mt-1">Make sure you have uploaded a resume with parsed skills.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {recommendations.map((rec) => (
            <div key={rec.id} className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 flex flex-col gap-4">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                {/* Title & Company */}
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

                {/* Actions */}
                <div className="flex flex-wrap gap-2 shrink-0">
                  <button
                    onClick={() => handleSave(rec.job_id)}
                    disabled={rec.is_saved}
                    className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-zinc-300 hover:bg-zinc-850 hover:text-white disabled:opacity-50 transition-all"
                  >
                    <Bookmark className="h-4 w-4" />
                    {rec.is_saved ? "Saved" : "Save"}
                  </button>
                  <button
                    onClick={() => handleDismiss(rec.job_id)}
                    className="rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-1.5 text-xs font-semibold text-zinc-400 hover:text-white transition-all"
                  >
                    Dismiss
                  </button>
                  <button
                    onClick={() => handleLogApplication(rec.job_id)}
                    className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition-all"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Track Apply
                  </button>
                </div>
              </div>

              {/* Description Snippet */}
              <p className="text-xs text-zinc-500 leading-relaxed max-w-4xl line-clamp-2">
                {rec.job.description}
              </p>

              {/* Explanations Section */}
              <div className="rounded-xl border border-indigo-950 bg-indigo-950/10 p-4 border-dashed">
                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block mb-1">
                  AI Recommendation Review
                </span>
                <p className="text-xs text-zinc-300 leading-relaxed italic pr-4">
                  "{rec.explanation}"
                </p>
              </div>

              {/* Auxiliary AI Resource Generators */}
              <div className="flex gap-4 border-t border-zinc-900 pt-4 mt-1 text-xs text-zinc-400">
                <button
                  onClick={() => generateOutreach("cover", rec.job)}
                  className="flex items-center gap-1.5 hover:text-white transition-colors"
                >
                  <FileText className="h-4 w-4 text-indigo-400" />
                  Generate Tailored Cover Letter
                </button>
                <button
                  onClick={() => generateOutreach("email", rec.job)}
                  className="flex items-center gap-1.5 hover:text-white transition-colors"
                >
                  <Mail className="h-4 w-4 text-indigo-400" />
                  Draft Recruiter Email
                </button>
                <a
                  href={rec.job.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 hover:text-white ml-auto transition-colors"
                >
                  Apply Directly
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Dynamic Cover Letter / Email drafting modal */}
      {modalType && activeJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl border border-zinc-800 bg-zinc-950 p-6 flex flex-col h-[80vh] justify-between">
            <div className="flex items-center justify-between border-b border-zinc-900 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">
                  {modalType === "cover" ? "Custom Cover Letter" : "Recruiter Email"}
                </h3>
                <p className="text-xs text-zinc-500">{activeJob.title} at {activeJob.company.name}</p>
              </div>
              <button
                onClick={() => {
                  setModalType(null);
                  setActiveJob(null);
                }}
                className="text-zinc-500 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 my-4 overflow-y-auto bg-zinc-900/40 border border-zinc-850 rounded-xl p-4 font-mono text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
              {generating ? (
                <div className="flex h-full items-center justify-center text-zinc-500">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
                  Drafting with GPT-4o-mini...
                </div>
              ) : (
                modalText
              )}
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-zinc-900">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(modalText);
                  alert("Copied to clipboard!");
                }}
                disabled={generating}
                className="rounded-lg bg-zinc-900 border border-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
              >
                Copy Content
              </button>
              <button
                onClick={() => {
                  setModalType(null);
                  setActiveJob(null);
                }}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
              >
                Close View
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
