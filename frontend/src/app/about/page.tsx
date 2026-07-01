import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Users, Code, Award, CheckCircle } from "lucide-react";

export default function About() {
  return (
    <div className="flex min-h-screen flex-col bg-black text-white">
      <Navbar />
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
            Empowering Careers with AI Matching
          </h1>
          <p className="mt-4 text-zinc-400 leading-relaxed text-lg">
            JobDiscovery AI was founded by a team of software engineers and recruiters who realized the traditional job search process is broken. We combine modern vector models and transparent rule filters to help candidates find relevant work.
          </p>
        </div>

        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-950 text-indigo-400 mb-4 border border-indigo-900">
              <Users className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">Candidate-First</h3>
            <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
              We focus purely on enabling job seekers to land interviews. No hidden fees or selling data to headhunters.
            </p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-950 text-indigo-400 mb-4 border border-indigo-900">
              <Code className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">Vector Match Engine</h3>
            <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
              Our 1536-dimensional vector similarity index processes natural language contexts to discover jobs matching raw skills.
            </p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-950 text-indigo-400 mb-4 border border-indigo-900">
              <Award className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">Automated Outreach</h3>
            <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
              Skip drafting cover letters and cold emails. Generate high-quality copy contextualized to the target position instantly.
            </p>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
