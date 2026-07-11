"use client";

import { useEffect, useState } from "react";
import { FileText, Calendar, Eye, AlertCircle } from "lucide-react";
import api from "@/lib/api";

export default function ResumeHistory() {
  const [resumes, setResumes] = useState<any[]>([]);
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const resList: any = await api.get("/resumes");
        setResumes(resList);
        if (resList.length > 0) {
          const verList: any = await api.get(`/resumes/${resList[0].id}/versions`);
          // Sort by version number descending so latest versions are on top
          verList.sort((a: any, b: any) => b.version_number - a.version_number);
          setVersions(verList);
          if (verList.length > 0) {
            setSelectedVersion(verList[0]);
          }
        }
      } catch (err) {
        console.error("Failed to load resume history", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Loading History...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Resume History</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Inspect, track, and compare details of all uploaded resume files and matching versions.
        </p>
      </div>

      {resumes.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/20 p-12 text-center">
          <p className="text-sm text-zinc-500">No resumes found. Please upload a resume to view history.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* Versions list */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 lg:col-span-1 space-y-4">
            <h3 className="text-base font-bold text-white uppercase tracking-wider text-zinc-400">
              Uploaded Versions
            </h3>
            <div className="space-y-2">
              {versions.map((ver) => (
                <button
                  key={ver.id}
                  onClick={() => setSelectedVersion(ver)}
                  className={`w-full text-left rounded-xl p-4 border transition-all ${
                    selectedVersion?.id === ver.id
                      ? "border-indigo-500 bg-indigo-950/10"
                      : "border-zinc-800 bg-zinc-900/20 hover:border-zinc-700"
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <span className="text-sm font-semibold text-white">Version {ver.version_number}</span>
                    <span className="rounded bg-indigo-950 border border-indigo-900 px-1.5 py-0.5 text-[10px] text-indigo-400 font-semibold">
                      ATS: {ver.parsed_data?.ats_score != null ? `${ver.parsed_data.ats_score}%` : "N/A"}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-1.5 text-xs text-zinc-500">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>{new Date(ver.created_at).toLocaleDateString()}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Version details view */}
          <div className="lg:col-span-2">
            {selectedVersion ? (
              <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 space-y-8">
                <div className="flex justify-between items-center border-b border-zinc-900 pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-white">Version {selectedVersion.version_number} Analysis</h3>
                    <p className="text-xs text-zinc-500 mt-0.5">Uploaded on {new Date(selectedVersion.created_at).toLocaleString()}</p>
                  </div>
                  <a
                    href={selectedVersion.file_path}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 hover:text-white transition-colors"
                  >
                    <Eye className="h-4 w-4" />
                    View Original
                  </a>
                </div>

                {/* Score Summary */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="rounded-xl border border-zinc-855 bg-zinc-900/10 p-4">
                    <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block">Quality score</span>
                    <span className="text-xl font-bold text-white mt-1 block">{selectedVersion.parsed_data?.quality_score}%</span>
                  </div>
                  <div className="rounded-xl border border-zinc-855 bg-zinc-900/10 p-4">
                    <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block">ATS Score</span>
                    <span className="text-xl font-bold text-white mt-1 block">{selectedVersion.parsed_data?.ats_score != null ? `${selectedVersion.parsed_data.ats_score}%` : "N/A"}</span>
                  </div>
                </div>

                {/* Skills parsed */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Extracted Profile Skills</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedVersion.skills?.map((s: any, idx: number) => (
                      <span key={idx} className="rounded-md bg-zinc-900 px-2.5 py-1 text-xs text-zinc-300 border border-zinc-850">
                        {s.skill_name} {s.years_experience ? `(${s.years_experience} yrs)` : ""}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Quality Suggestions */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Suggestions for Improvement</h4>
                  <ul className="space-y-2 text-xs text-zinc-300">
                    {selectedVersion.parsed_data?.suggestions?.map((item: string, idx: number) => (
                      <li key={idx} className="flex gap-2">
                        <AlertCircle className="h-4 w-4 text-indigo-400 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-12 text-center text-zinc-500">
                Select a version on the left panel to inspect parsing reports.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
