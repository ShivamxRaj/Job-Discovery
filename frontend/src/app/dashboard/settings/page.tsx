"use client";

import { useEffect, useState } from "react";
import { Check, Settings, Save, AlertCircle } from "lucide-react";
import api from "@/lib/api";

export default function SettingsPage() {
  const [locations, setLocations] = useState("");
  const [roles, setRoles] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [isRemote, setIsRemote] = useState(false);
  const [companyExclusions, setCompanyExclusions] = useState("");
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const fetchPrefs = async () => {
      try {
        const data: any = await api.get("/auth/preferences");
        setLocations(data.preferred_locations?.join(", ") || "");
        setRoles(data.preferred_roles?.join(", ") || "");
        setMinSalary(data.min_salary?.toString() || "");
        setIsRemote(data.is_remote || false);
        setCompanyExclusions(data.company_exclusions?.join(", ") || "");
      } catch (err) {
        console.error("Failed to load preferences", err);
      } finally {
        setLoading(false);
      }
    };
    fetchPrefs();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);

    const payload = {
      preferred_locations: locations.split(",").map(s => s.trim()).filter(Boolean),
      preferred_roles: roles.split(",").map(s => s.trim()).filter(Boolean),
      min_salary: minSalary ? Number(minSalary) : null,
      is_remote: isRemote,
      company_exclusions: companyExclusions.split(",").map(s => s.trim()).filter(Boolean)
    };

    try {
      await api.put("/auth/preferences", payload);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save settings", err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent mr-2" />
        Loading Settings...
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Job Match Preferences</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Configure filters and preferences used by the AI Matching and Rule Engine.
        </p>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
        <form onSubmit={handleSave} className="space-y-6">
          {success && (
            <div className="rounded-lg bg-emerald-950/40 border border-emerald-900/60 p-3 text-sm text-emerald-400 flex items-center gap-2">
              <Check className="h-4.5 w-4.5 shrink-0" />
              <span>Preferences saved successfully! AI recommender matches updated.</span>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label htmlFor="pref-roles" className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Target Roles (comma-separated)
              </label>
              <input
                id="pref-roles"
                type="text"
                value={roles}
                onChange={(e) => setRoles(e.target.value)}
                className="block w-full rounded-lg border border-zinc-800 bg-zinc-900/50 px-3.5 py-2.5 text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none transition-colors text-sm"
                placeholder="Software Engineer, Backend Developer"
              />
            </div>

            <div>
              <label htmlFor="pref-locations" className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Preferred Locations (comma-separated)
              </label>
              <input
                id="pref-locations"
                type="text"
                value={locations}
                onChange={(e) => setLocations(e.target.value)}
                className="block w-full rounded-lg border border-zinc-800 bg-zinc-900/50 px-3.5 py-2.5 text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none transition-colors text-sm"
                placeholder="San Francisco, New York, London"
              />
            </div>

            <div>
              <label htmlFor="pref-salary" className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Minimum Annual Salary ($)
              </label>
              <input
                id="pref-salary"
                type="number"
                value={minSalary}
                onChange={(e) => setMinSalary(e.target.value)}
                className="block w-full rounded-lg border border-zinc-800 bg-zinc-900/50 px-3.5 py-2.5 text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none transition-colors text-sm"
                placeholder="100000"
              />
            </div>

            <div>
              <label htmlFor="exclusions" className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Excluded Companies (comma-separated)
              </label>
              <input
                id="exclusions"
                type="text"
                value={companyExclusions}
                onChange={(e) => setCompanyExclusions(e.target.value)}
                className="block w-full rounded-lg border border-zinc-800 bg-zinc-900/50 px-3.5 py-2.5 text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none transition-colors text-sm"
                placeholder="Meta, Netflix"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 border-t border-zinc-900 pt-4">
            <input
              id="pref-remote"
              type="checkbox"
              checked={isRemote}
              onChange={(e) => setIsRemote(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0 focus:outline-none"
            />
            <label htmlFor="pref-remote" className="text-sm font-medium text-zinc-300">
              Prioritize Remote Job Listings
            </label>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              <Save className="h-4.5 w-4.5" />
              {saving ? "Saving..." : "Save Preferences"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
