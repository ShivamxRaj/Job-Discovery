"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Briefcase, Menu, X, User as UserIcon, LogOut } from "lucide-react";

export default function Navbar() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setToken(localStorage.getItem("token"));
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    router.push("/");
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-zinc-800 bg-black/80 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 justify-between items-center">
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2 text-xl font-bold tracking-tight text-white">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600">
                <Briefcase className="h-5 w-5 text-white" />
              </div>
              <span>Job<span className="text-indigo-400">Discovery</span></span>
            </Link>
            <div className="hidden md:flex items-center gap-6 ml-10">
              <Link href="/about" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
                About
              </Link>
              <Link href="/pricing" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
                Pricing
              </Link>
              {token && (
                <Link href="/dashboard" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
                  Dashboard
                </Link>
              )}
            </div>
          </div>

          <div className="hidden md:flex items-center gap-4">
            {token ? (
              <div className="flex items-center gap-4">
                <Link 
                  href="/dashboard/profile"
                  className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900 px-4 py-1.5 text-sm font-medium text-zinc-200 hover:bg-zinc-800 transition-colors"
                >
                  <UserIcon className="h-4 w-4" />
                  Profile
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 rounded-lg bg-red-950/40 border border-red-900/60 px-3 py-1.5 text-sm font-medium text-red-400 hover:bg-red-900/40 transition-all"
                >
                  <LogOut className="h-4 w-4" />
                  Logout
                </button>
              </div>
            ) : (
              <>
                <Link href="/login" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 hover:shadow-[0_0_15px_rgba(79,70,229,0.4)] transition-all"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>

          <div className="flex md:hidden">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="inline-flex items-center justify-center rounded-lg p-2 text-zinc-400 hover:bg-zinc-900 hover:text-white"
            >
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden border-b border-zinc-800 bg-black px-4 pt-2 pb-4 space-y-2">
          <Link
            href="/about"
            onClick={() => setIsOpen(false)}
            className="block rounded-lg px-3 py-2 text-base font-medium text-zinc-400 hover:bg-zinc-900 hover:text-white"
          >
            About
          </Link>
          <Link
            href="/pricing"
            onClick={() => setIsOpen(false)}
            className="block rounded-lg px-3 py-2 text-base font-medium text-zinc-400 hover:bg-zinc-900 hover:text-white"
          >
            Pricing
          </Link>
          {token ? (
            <>
              <Link
                href="/dashboard"
                onClick={() => setIsOpen(false)}
                className="block rounded-lg px-3 py-2 text-base font-medium text-zinc-400 hover:bg-zinc-900 hover:text-white"
              >
                Dashboard
              </Link>
              <Link
                href="/dashboard/profile"
                onClick={() => setIsOpen(false)}
                className="block rounded-lg px-3 py-2 text-base font-medium text-zinc-400 hover:bg-zinc-900 hover:text-white"
              >
                Profile
              </Link>
              <button
                onClick={() => {
                  setIsOpen(false);
                  handleLogout();
                }}
                className="w-full text-left block rounded-lg px-3 py-2 text-base font-medium text-red-400 hover:bg-red-950/20"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                onClick={() => setIsOpen(false)}
                className="block rounded-lg px-3 py-2 text-base font-medium text-zinc-400 hover:bg-zinc-900 hover:text-white"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                onClick={() => setIsOpen(false)}
                className="block text-center rounded-lg bg-indigo-600 px-3 py-2 text-base font-medium text-white"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
