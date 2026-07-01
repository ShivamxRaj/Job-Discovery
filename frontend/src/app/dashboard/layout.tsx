"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  Upload,
  History,
  Briefcase,
  Bookmark,
  CalendarDays,
  Settings,
  User,
  Bell,
  Kanban,
  Shield,
  LogOut,
  Menu,
  X
} from "lucide-react";
import api from "@/lib/api";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    const fetchUser = async () => {
      try {
        const u = await api.get("/auth/me");
        setUser(u);
        setLoading(false);
      } catch (err) {
        localStorage.removeItem("token");
        router.push("/login");
      }
    };

    fetchUser();
  }, [router]);

  const navItems = [
    { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { name: "Upload Resume", href: "/dashboard/resume-upload", icon: Upload },
    { name: "Resume History", href: "/dashboard/resume-history", icon: History },
    { name: "Recommended Jobs", href: "/dashboard/recommended-jobs", icon: Briefcase },
    { name: "Saved Jobs", href: "/dashboard/saved-jobs", icon: Bookmark },
    { name: "Applications", href: "/dashboard/applications", icon: Kanban },
    { name: "Interviews", href: "/dashboard/interviews", icon: CalendarDays },
    { name: "Notifications", href: "/dashboard/notifications", icon: Bell },
    { name: "Preferences", href: "/dashboard/settings", icon: Settings },
    { name: "Profile", href: "/dashboard/profile", icon: User },
  ];

  if (user?.is_superuser) {
    navItems.push({ name: "Admin Portal", href: "/dashboard/admin", icon: Shield });
  }

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/");
  };

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-black text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          <span className="text-sm font-medium text-zinc-400">Loading Dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-black text-white">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950/60 backdrop-blur-lg">
        <div className="flex h-16 items-center border-b border-zinc-800 px-6">
          <Link href="/" className="flex items-center gap-2 text-lg font-bold tracking-tight text-white">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-indigo-600">
              <Briefcase className="h-4.5 w-4.5 text-white" />
            </div>
            <span>Job<span className="text-indigo-400">Discovery</span></span>
          </Link>
        </div>

        <nav className="flex-1 space-y-1 px-4 py-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                  active
                    ? "bg-indigo-600 text-white"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-white"
                }`}
              >
                <Icon className={`h-5 w-5 shrink-0 ${active ? "text-white" : "text-zinc-400 group-hover:text-white"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-zinc-800 p-4">
          <div className="flex items-center justify-between rounded-xl bg-zinc-900/50 p-3 border border-zinc-800/80">
            <div className="truncate pr-2">
              <p className="truncate text-xs font-semibold text-white">{user?.email}</p>
              <p className="text-[10px] text-zinc-500 capitalize">Candidate Account</p>
            </div>
            <button
              onClick={handleLogout}
              className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-red-400 transition-colors"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Sidebar - Mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden bg-black/80 backdrop-blur-sm">
          <div className="w-64 border-r border-zinc-800 bg-zinc-950 p-6 flex flex-col">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-6">
              <span className="text-lg font-bold text-white">Menu</span>
              <button onClick={() => setSidebarOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="h-6 w-6" />
              </button>
            </div>
            <nav className="flex-1 space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${
                      active ? "bg-indigo-600 text-white" : "text-zinc-400 hover:bg-zinc-900 hover:text-white"
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
            <button
              onClick={handleLogout}
              className="mt-auto flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-red-400 hover:bg-red-950/20"
            >
              <LogOut className="h-5 w-5" />
              Logout
            </button>
          </div>
        </div>
      )}

      {/* Content wrapper */}
      <div className="flex flex-1 flex-col overflow-y-auto">
        <header className="flex h-16 items-center justify-between border-b border-zinc-800 bg-zinc-950/20 px-6 lg:justify-end">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded border border-zinc-850 p-1.5 text-zinc-400 hover:bg-zinc-900 hover:text-white lg:hidden"
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex items-center gap-4">
            <span className="rounded-full bg-zinc-900 px-3 py-1 text-xs font-semibold text-zinc-400 border border-zinc-800">
              Active Session
            </span>
          </div>
        </header>

        <main className="flex-1 p-6 sm:p-10">{children}</main>
      </div>
    </div>
  );
}
