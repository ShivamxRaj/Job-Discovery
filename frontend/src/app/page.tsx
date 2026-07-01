"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight, ShieldCheck, Zap, Cpu, BarChart3 } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function Home() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.15 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
  };

  return (
    <div className="flex min-h-screen flex-col bg-black text-white selection:bg-indigo-600 selection:text-white">
      <Navbar />

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-16 md:pt-32 md:pb-28">
        {/* Glow Effects */}
        <div className="absolute top-1/4 left-1/2 -z-10 h-96 w-96 -translate-x-1/2 rounded-full bg-indigo-900/20 blur-[120px]" />
        <div className="absolute top-10 left-10 -z-10 h-72 w-72 rounded-full bg-blue-900/10 blur-[100px]" />

        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-950/20 px-3 py-1.5 text-xs font-semibold text-indigo-400 mb-6"
          >
            <Sparkles className="h-3 w-3" />
            Next-Gen AI Matchmaking
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-4xl font-extrabold tracking-tight sm:text-6xl max-w-4xl mx-auto leading-[1.1] bg-gradient-to-r from-white via-zinc-200 to-zinc-500 bg-clip-text text-transparent"
          >
            Discover Your Perfect Job Role with AI Matching
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-6 text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed"
          >
            Stop scrolling generic boards. Upload your resume and let our vector matching engine find roles matching your skills, and generate custom outreach resources instantly.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-10 flex flex-wrap justify-center gap-4"
          >
            <Link
              href="/register"
              className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3.5 text-sm font-semibold text-white hover:bg-indigo-500 hover:shadow-[0_0_20px_rgba(79,70,229,0.5)] transition-all"
            >
              Get Started Free
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/pricing"
              className="rounded-xl border border-zinc-800 bg-zinc-900/50 px-6 py-3.5 text-sm font-semibold text-zinc-300 hover:bg-zinc-800 hover:text-white transition-all"
            >
              View Pricing
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="border-t border-zinc-900 bg-zinc-950/20 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl text-white">
              End-to-End AI Placement Suite
            </h2>
            <p className="mt-4 text-zinc-400">
              Powerful tools built specifically to optimize your application success metrics.
            </p>
          </div>

          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4"
          >
            {/* Feature 1 */}
            <motion.div variants={itemVariants} className="group rounded-2xl border border-zinc-800 bg-zinc-950 p-6 hover:border-indigo-500/50 transition-all">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-950/50 border border-indigo-900 text-indigo-400 mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-all">
                <Cpu className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-white">AI Resume Parsing</h3>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                Extract skills, projects, and work histories with 99% accuracy using custom LLM parsers.
              </p>
            </motion.div>

            {/* Feature 2 */}
            <motion.div variants={itemVariants} className="group rounded-2xl border border-zinc-800 bg-zinc-950 p-6 hover:border-indigo-500/50 transition-all">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-950/50 border border-indigo-900 text-indigo-400 mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-all">
                <BarChart3 className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-white">ATS & Quality Scoring</h3>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                Receive concrete scores, format flags, and specific textual bullet improvement recommendations.
              </p>
            </motion.div>

            {/* Feature 3 */}
            <motion.div variants={itemVariants} className="group rounded-2xl border border-zinc-800 bg-zinc-950 p-6 hover:border-indigo-500/50 transition-all">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-950/50 border border-indigo-900 text-indigo-400 mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-all">
                <Zap className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-white">Vector Match Engine</h3>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                Find postings using pgvector embedding cosine comparisons merged with custom filter rule sets.
              </p>
            </motion.div>

            {/* Feature 4 */}
            <motion.div variants={itemVariants} className="group rounded-2xl border border-zinc-800 bg-zinc-950 p-6 hover:border-indigo-500/50 transition-all">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-950/50 border border-indigo-900 text-indigo-400 mb-5 group-hover:bg-indigo-600 group-hover:text-white transition-all">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-white">Outreach Generation</h3>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                Create tailored cover letters and cold recruiter emails mapped to job details instantly.
              </p>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Steps Section */}
      <section className="py-20 bg-black">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl text-white">
                How JobDiscovery AI Works
              </h2>
              <p className="mt-4 text-zinc-400 leading-relaxed">
                Our recommendation loop is engineered to build a personalized job application funnel in seconds.
              </p>
              
              <div className="mt-10 space-y-6">
                <div className="flex gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-950 border border-indigo-900 text-sm font-semibold text-indigo-400">1</div>
                  <div>
                    <h4 className="text-base font-semibold text-white">Upload & Parse</h4>
                    <p className="text-sm text-zinc-400 mt-1">Upload your PDF or Docx resume. We parse and construct your profile vector.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-950 border border-indigo-900 text-sm font-semibold text-indigo-400">2</div>
                  <div>
                    <h4 className="text-base font-semibold text-white">Vector Recommendation Match</h4>
                    <p className="text-sm text-zinc-400 mt-1">Our engine matches embeddings against 10,000+ jobs, executing custom rule checks.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-950 border border-indigo-900 text-sm font-semibold text-indigo-400">3</div>
                  <div>
                    <h4 className="text-base font-semibold text-white">Generate Cover Letters & Track</h4>
                    <p className="text-sm text-zinc-400 mt-1">Generate tailored cover letters and HR messages, then log dates in our kanban board.</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="relative rounded-2xl border border-zinc-800 bg-zinc-950/60 p-8 shadow-2xl overflow-hidden">
              <div className="absolute top-0 right-0 h-40 w-40 rounded-full bg-indigo-600/10 blur-[40px] -z-10" />
              <div className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-6">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full bg-red-500" />
                  <span className="h-3 w-3 rounded-full bg-yellow-500" />
                  <span className="h-3 w-3 rounded-full bg-green-500" />
                </div>
                <span className="text-xs text-zinc-500 font-mono">match_run_pipeline.json</span>
              </div>
              <pre className="text-xs font-mono text-indigo-300 overflow-x-auto space-y-1">
                {`{
  "status": "completed",
  "resume_version": "v1.4.0",
  "vector_dimensions": 1536,
  "candidates_retrieved": 100,
  "rule_engine_filtering": {
    "skill_match": "weighted_0.35",
    "is_remote_match": true,
    "salary_range_valid": "min_salary >= 120k"
  },
  "top_matches": [
    { "role": "Senior Engineer", "score": 94.2, "explanation_generated": true },
    { "role": "Full Stack Lead", "score": 89.5, "explanation_generated": true }
  ]
}`}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="border-t border-zinc-900 bg-zinc-950/40 py-20 relative overflow-hidden">
        <div className="absolute bottom-0 left-0 right-0 h-60 bg-gradient-to-t from-indigo-950/10 to-transparent -z-10 blur-2xl" />
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-white">
            Ready to Accelerate Your Placement Funnel?
          </h2>
          <p className="mt-4 text-zinc-400 max-w-xl mx-auto">
            Get instant access to AI matching scores, cover letter drafts, and personalized job recommendations.
          </p>
          <div className="mt-8">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-8 py-4 text-sm font-semibold text-white hover:bg-indigo-500 hover:shadow-[0_0_20px_rgba(79,70,229,0.5)] transition-all"
            >
              Sign Up Now
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
