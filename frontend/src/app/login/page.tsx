"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Briefcase, ArrowRight } from "lucide-react";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Handle callback response from Google Identity Services
  const handleGoogleResponse = async (response: any) => {
    setError(null);
    setLoading(true);
    try {
      const data: any = await api.post("/auth/google", {
        credential: response.credential,
      });
      localStorage.setItem("token", data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to authenticate with Google.");
    } finally {
      setLoading(false);
    }
  };

  // Quick dev-only trigger for testing without needing setup
  const triggerMockGoogleLogin = async () => {
    await handleGoogleResponse({
      credential: "mock_email:google.tester@gmail.com",
    });
  };

  useEffect(() => {
    // Load Google script dynamically
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "placeholder-google-client-id";
      if ((window as any).google) {
        (window as any).google.accounts.id.initialize({
          client_id: clientId,
          callback: handleGoogleResponse,
        });
        (window as any).google.accounts.id.renderButton(
          document.getElementById("google-signin-btn"),
          {
            theme: "filled_black",
            size: "large",
            width: 382,
            text: "signin_with",
            shape: "rectangular",
            logo_alignment: "center",
          }
        );
      }
    };
    document.body.appendChild(script);

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data: any = await api.post("/auth/login", { email, password });
      localStorage.setItem("token", data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to login. Please check credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-black text-white">
      <Navbar />
      <div className="flex flex-1 items-center justify-center px-4 py-16 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-8 rounded-2xl border border-zinc-800 bg-zinc-950 p-8 shadow-2xl">
          <div className="text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 mb-4">
              <Briefcase className="h-6 w-6 text-white" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white">Sign in to your account</h2>
            <p className="mt-2 text-sm text-zinc-400">
              Or{" "}
              <Link href="/register" className="font-semibold text-indigo-400 hover:text-indigo-350">
                register a new account
              </Link>
            </p>
          </div>

          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="rounded-lg bg-red-950/40 border border-red-900/60 p-3 text-sm text-red-400">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label htmlFor="email-address" className="block text-sm font-medium text-zinc-300">
                  Email Address
                </label>
                <input
                  id="email-address"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-2.5 text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none transition-colors text-sm"
                  placeholder="name@example.com"
                />
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label htmlFor="password" className="block text-sm font-medium text-zinc-300">
                    Password
                  </label>
                  <Link href="/forgot-password" className="text-xs font-semibold text-indigo-400 hover:text-indigo-350">
                    Forgot password?
                  </Link>
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-2.5 text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none transition-colors text-sm"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="group flex w-full justify-center items-center gap-2 rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 transition-all disabled:opacity-50"
              >
                {loading ? "Signing in..." : "Sign In"}
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </form>

          {/* Social Sign In Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <div className="w-full border-t border-zinc-800"></div>
            </div>
            <div className="relative flex justify-center text-xs text-zinc-400 uppercase">
              <span className="bg-zinc-950 px-2">Or continue with</span>
            </div>
          </div>

          {/* Google Login Button Container */}
          <div className="flex justify-center w-full">
            <div id="google-signin-btn"></div>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
