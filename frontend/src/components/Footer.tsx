import Link from "next/link";
import { Briefcase } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-zinc-850 bg-black py-10 mt-auto">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2 text-lg font-semibold text-white">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-indigo-600">
              <Briefcase className="h-4 w-4 text-white" />
            </div>
            <span>Job<span className="text-indigo-400">Discovery</span></span>
          </div>
          <p className="text-xs text-zinc-500">
            &copy; {new Date().getFullYear()} JobDiscovery AI Inc. All rights reserved. Built with Next.js 15, FastAPI & pgvector.
          </p>
          <div className="flex gap-4 text-xs text-zinc-500">
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
