"use client";

import { useState } from "react";
import { Upload, CheckCircle2, AlertCircle, FileText, ArrowRight } from "lucide-react";
import api from "@/lib/api";

/**
 * Renders a resume upload form and displays parsing results, quality metrics, ATS compatibility, recommendations, and extracted skills.
 */
export default function ResumeUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("My Resume");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file to upload.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);

    try {
      const data: any = await api.post("/resumes/upload", formData);
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to parse resume.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Upload Resume</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Upload your PDF or Word document. We will analyze your profile and compute ATS readiness scores.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Upload form container */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 lg:col-span-1 h-fit">
          <h3 className="text-base font-bold text-white mb-4">Select Resume File</h3>
          <form onSubmit={handleUpload} className="space-y-6">
            {error && (
              <div className="rounded-lg bg-red-950/40 border border-red-900/60 p-3 text-sm text-red-400 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label htmlFor="resume-title" className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Resume Title
              </label>
              <input
                id="resume-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="block w-full rounded-lg border border-zinc-800 bg-zinc-900/50 px-3.5 py-2 text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none transition-colors text-sm"
                placeholder="My Resume"
              />
            </div>

            <div>
              <span className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Resume Document
              </span>
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-zinc-800 rounded-xl py-8 px-4 cursor-pointer hover:border-zinc-700 hover:bg-zinc-900/10 transition-all text-center">
                <Upload className="h-8 w-8 text-zinc-500 mb-3" />
                <span className="text-sm font-semibold text-zinc-300">
                  {file ? file.name : "Choose File"}
                </span>
                <span className="text-xs text-zinc-500 mt-1">PDF, DOCX up to 5MB</span>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            </div>

            <button
              type="submit"
              disabled={loading || !file}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {loading ? "Uploading & Analyzing..." : "Submit File"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
        </div>

        {/* Output details block */}
        <div className="lg:col-span-2 space-y-6">
          {loading && (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-12 text-center flex flex-col items-center gap-4 justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
              <p className="text-sm text-zinc-400">
                Running AI parser... extracting skills and generating embeddings...
              </p>
            </div>
          )}

          {result && (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 space-y-8">
              <div className="flex items-center gap-2 text-emerald-400 font-bold">
                <CheckCircle2 className="h-5 w-5" />
                <span>Resume Processed Successfully!</span>
              </div>

              {/* Score charts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="rounded-xl border border-zinc-850 bg-zinc-900/20 p-5 text-center flex flex-col items-center justify-center">
                  <span className="text-2xl font-black text-indigo-400">
                    {result.parsed_data?.quality_score}%
                  </span>
                  <h4 className="text-sm font-bold text-white mt-1">Quality Assessment Score</h4>
                  <p className="text-xs text-zinc-500 mt-1">Overall spelling, formatting, and impact metrics.</p>
                </div>
                <div className="rounded-xl border border-zinc-850 bg-zinc-900/20 p-5 text-center flex flex-col items-center justify-center">
                  <span className="text-2xl font-black text-indigo-400">
                    {result.parsed_data?.ats_score != null ? `${result.parsed_data.ats_score}%` : "N/A"}
                  </span>
                  <h4 className="text-sm font-bold text-white mt-1">ATS Compatibility Meter</h4>
                  <p className="text-xs text-zinc-500 mt-1">Keyword mapping and parser compliance checks.</p>
                </div>
              </div>

              {/* Suggestions */}
              <div className="space-y-3">
                <h4 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
                  ATS Improvement Recommendations
                </h4>
                <ul className="space-y-2 text-xs text-zinc-300">
                  {result.parsed_data?.suggestions?.map((item: string, idx: number) => (
                    <li key={idx} className="flex gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 shrink-0 mt-1.5" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Skills Normalized */}
              <div className="space-y-3">
                <h4 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
                  Extracted & Normalized Skills
                </h4>
                <div className="flex flex-wrap gap-2">
                  {result.skills?.map((s: any, idx: number) => (
                    <span
                      key={idx}
                      className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-zinc-300 border border-zinc-850"
                    >
                      {s.skill_name} {s.years_experience ? `(${s.years_experience} yrs)` : ""}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {!result && !loading && (
            <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/20 p-12 text-center flex flex-col items-center justify-center">
              <FileText className="h-12 w-12 text-zinc-600 mb-3" />
              <p className="text-sm text-zinc-400">
                Submit your resume on the left panel to inspect quality metrics and matching lists.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
