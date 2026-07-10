"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, FileText, Briefcase, HelpCircle, CheckCircle, Clock } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";

export default function Dashboard() {
  const [stats, setStats] = useState({
    resumes: 0,
    recommendations: 0,
    applications: 0,
    interviews: 0
  });
  const [latestVersion, setLatestVersion] = useState<any>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      // 1. Fetch user profile immediately for instant notification
      api.get("/auth/me").then((currentUser: any) => {
        if (!sessionStorage.getItem("welcomed") && currentUser) {
          toast.success(`Welcome to JobDiscovery, ${currentUser.full_name || "User"}!`, {
            description: "Your personalized job search command center.",
            duration: 5000,
          });
          sessionStorage.setItem("welcomed", "true");
        }
      }).catch(err => console.error("Failed to load user profile", err));

      // 2. Fetch all dashboard stats in parallel to drastically reduce load time
      try {
        const [resumesData, recsData, appsData] = await Promise.all([
          api.get("/resumes").catch(() => []),
          api.get("/jobs/recommendations").catch(() => []),
          api.get("/applications").catch(() => [])
        ]);

        const resumes: any[] = resumesData || [];
        const recs: any[] = recsData || [];
        const apps: any[] = appsData || [];
        
        let latest = null;
        let totalVersionsCount = 0;
        
        if (resumes.length > 0) {
          try {
            const versions: any = await api.get(`/resumes/${resumes[0].id}/versions`) || [];
            if (versions.length > 0) {
              totalVersionsCount = versions.length;
              versions.sort((a: any, b: any) => b.version_number - a.version_number);
              latest = versions[0];
            }
          } catch (err) {
            console.error("Failed to load resume versions", err);
          }
        }

        const interviewsCount = apps.filter((a: any) => a.status === "Interview").length;

        setStats({
          resumes: totalVersionsCount > 0 ? totalVersionsCount : resumes.length,
          recommendations: recs.length,
          applications: apps.length,
          interviews: interviewsCount
        });
        setLatestVersion(latest);
      } catch (err) {
        console.error("Error fetching dashboard data", err);
      }
    };

    fetchDashboardData();
  }, []);

  const cardItems = [
    { name: "Resumes Uploaded", value: stats.resumes, desc: "Active resume versions", href: "/dashboard/resume-history", icon: FileText, color: "text-blue-400" },
    { name: "AI Recommendations", value: stats.recommendations, desc: "Personalized matching positions", href: "/dashboard/recommended-jobs", icon: Sparkles, color: "text-indigo-400" },
    { name: "Applications Logged", value: stats.applications, desc: "Jobs tracked in pipeline", href: "/dashboard/applications", icon: Briefcase, color: "text-green-400" },
    { name: "Scheduled Interviews", value: stats.interviews, desc: "Upcoming interview dates", href: "/dashboard/interviews", icon: Clock, color: "text-purple-400" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Overview</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Welcome to your job search command center.
        </p>
      </div>

      {/* Grid Stats */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {cardItems.map((c) => {
          const Icon = c.icon;
          return (
            <Link
              key={c.name}
              href={c.href}
              className="group rounded-2xl border border-zinc-800 bg-zinc-950 p-6 hover:border-zinc-700 transition-all hover:bg-zinc-900/40"
            >
              <div className="flex justify-between items-start">
                <span className="text-sm font-semibold text-zinc-400">{c.name}</span>
                <Icon className={`h-5 w-5 ${c.color} group-hover:scale-110 transition-transform`} />
              </div>
              <p className="mt-3 text-3xl font-extrabold text-white">{c.value}</p>
              <p className="mt-1 text-xs text-zinc-500">{c.desc}</p>
            </Link>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Latest Profile Quality */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold text-white mb-2">Resume Quality Score</h3>
            <p className="text-sm text-zinc-400 mb-6">Evaluation details for your latest uploaded resume.</p>
            
            {latestVersion ? (
              <div className="space-y-6">
                <div className="flex items-center gap-6">
                  <div className="relative flex h-24 w-24 shrink-0 items-center justify-center rounded-full border-4 border-indigo-500 bg-indigo-950/20 text-2xl font-black text-indigo-400">
                    {latestVersion.parsed_data?.quality_score != null 
                      ? `${latestVersion.parsed_data.quality_score}%` 
                      : '...'}
                  </div>
                  <div>
                    <h4 className="font-semibold text-white">ATS Compatibility Score</h4>
                    <p className="text-xs text-zinc-500 mt-1">
                      {latestVersion.parsed_data?.quality_score != null
                        ? "Based on keyword density, standard layout schema, and clean headings."
                        : "Processing your resume data... please wait or refresh shortly."}
                    </p>
                    <div className="mt-2 h-2.5 w-48 rounded-full bg-zinc-800 overflow-hidden">
                      <div 
                        className="h-full bg-indigo-500 transition-all duration-500" 
                        style={{ width: `${latestVersion.parsed_data?.ats_score || 0}%` }}
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-semibold text-zinc-400">Key Suggestions:</span>
                  <ul className="space-y-1.5">
                    {latestVersion.parsed_data?.suggestions && latestVersion.parsed_data.suggestions.length > 0 ? (
                      latestVersion.parsed_data.suggestions.slice(0, 3).map((s: string, idx: number) => {
                        const isError = s.toLowerCase().includes("failed") || s.toLowerCase().includes("error");
                        return (
                          <li key={idx} className="flex gap-2 text-xs text-zinc-300">
                            {isError ? (
                              <HelpCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
                            ) : (
                              <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                            )}
                            <span className={isError ? "text-red-400" : ""}>{s}</span>
                          </li>
                        );
                      })
                    ) : (
                      <li className="flex gap-2 text-xs text-zinc-300 items-center">
                        <Clock className="h-4 w-4 text-zinc-500 shrink-0" />
                        <span>Analyzing resume...</span>
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            ) : (
              <div className="text-center py-10 border border-dashed border-zinc-800 rounded-xl bg-zinc-900/20">
                <p className="text-sm text-zinc-500">Please upload a resume version to check ATS score metrics.</p>
                <Link
                  href="/dashboard/resume-upload"
                  className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors"
                >
                  Upload Now
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Quick Tips */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
          <h3 className="text-lg font-bold text-white mb-2">System Status</h3>
          <p className="text-sm text-zinc-400 mb-6">How to optimize your AI Recommendation matching loop.</p>
          
          <div className="space-y-4 text-xs text-zinc-300">
            <div className="flex gap-3 items-start border-b border-zinc-900 pb-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-indigo-950 text-indigo-400 border border-indigo-900">1</span>
              <div>
                <h5 className="font-semibold text-white">Customize Job Preferences</h5>
                <p className="text-zinc-500 mt-1">Configure role choices and location rules under Preferences to filter matching results.</p>
              </div>
            </div>
            <div className="flex gap-3 items-start border-b border-zinc-900 pb-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-indigo-950 text-indigo-400 border border-indigo-900">2</span>
              <div>
                <h5 className="font-semibold text-white">Review Match Explanation</h5>
                <p className="text-zinc-500 mt-1">AI generates customized reviews on match strengths and missing skill flags for each role.</p>
              </div>
            </div>
            <div className="flex gap-3 items-start">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-indigo-950 text-indigo-400 border border-indigo-900">3</span>
              <div>
                <h5 className="font-semibold text-white">Check Mail Digest Daily</h5>
                <p className="text-zinc-500 mt-1">Celery triggers a daily crawl matching newly scraped jobs, sending summaries directly to your inbox.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
