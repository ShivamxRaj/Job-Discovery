"use client";

import { useEffect, useState } from "react";
import { User, Mail, ShieldAlert, Award } from "lucide-react";
import api from "@/lib/api";

export default function Profile() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await api.get("/auth/me");
        setProfile(data);
      } catch (err) {
        console.error("Failed to load user profile", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Loading Profile...
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Profile Details</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Manage your personal account credentials and security roles.
        </p>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6 space-y-6">
        <div className="flex items-center gap-4 border-b border-zinc-900 pb-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-indigo-950 text-indigo-400 border border-indigo-900 text-2xl font-bold">
            {profile?.email[0].toUpperCase()}
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Candidate</h3>
            <p className="text-xs text-zinc-500 mt-0.5">Account ID: #{profile?.id}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3 text-xs text-zinc-300">
            <Mail className="h-4.5 w-4.5 text-zinc-500 shrink-0" />
            <div>
              <p className="font-semibold text-zinc-400">Email Address</p>
              <p className="text-white mt-0.5">{profile?.email}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-zinc-300">
            <Award className="h-4.5 w-4.5 text-zinc-500 shrink-0" />
            <div>
              <p className="font-semibold text-zinc-400">Account Role</p>
              <p className="text-white mt-0.5 capitalize">{profile?.is_superuser ? "Superuser Admin" : "Standard Candidate"}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-zinc-300">
            <ShieldAlert className="h-4.5 w-4.5 text-zinc-500 shrink-0" />
            <div>
              <p className="font-semibold text-zinc-400">Status</p>
              <p className="text-emerald-400 mt-0.5 font-semibold">Active</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
