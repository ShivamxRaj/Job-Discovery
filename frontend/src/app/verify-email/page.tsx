"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Briefcase, CheckCircle, XCircle, Loader2 } from "lucide-react";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [statusState, setStatusState] = useState<"verifying" | "success" | "error">("verifying");
  const [errorMessage, setErrorMessage] = useState("Invalid or expired verification token.");

  useEffect(() => {
    if (!token) {
      setStatusState("error");
      setErrorMessage("Verification token is missing from the link.");
      return;
    }

    const performVerification = async () => {
      try {
        await api.post("/auth/verify-email", { token });
        setStatusState("success");
      } catch (err: any) {
        setStatusState("error");
        setErrorMessage(err.message || "Email verification failed. The link may have expired.");
      }
    };

    performVerification();
  }, [token]);

  return (
    <div className="w-full max-w-md space-y-8 rounded-2xl border border-zinc-800 bg-zinc-950 p-8 shadow-2xl text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 mb-4">
        <Briefcase className="h-6 w-6 text-white" />
      </div>

      {statusState === "verifying" && (
        <div className="space-y-4 py-8">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-indigo-500" />
          <h2 className="text-2xl font-bold text-white">Verifying your email</h2>
          <p className="text-zinc-400 text-sm">
            Please wait while we confirm your email address.
          </p>
        </div>
      )}

      {statusState === "success" && (
        <div className="space-y-4 py-8">
          <CheckCircle className="mx-auto h-16 w-16 text-emerald-500" />
          <h2 className="text-2xl font-bold text-white">Email Verified!</h2>
          <p className="text-zinc-400 text-sm">
            Your email address has been successfully verified. You can now access your dashboard.
          </p>
          <div className="pt-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-all"
            >
              Go to Dashboard
            </Link>
          </div>
        </div>
      )}

      {statusState === "error" && (
        <div className="space-y-4 py-8">
          <XCircle className="mx-auto h-16 w-16 text-red-500" />
          <h2 className="text-2xl font-bold text-white">Verification Failed</h2>
          <p className="text-zinc-400 text-sm">{errorMessage}</p>
          <div className="pt-4">
            <Link
              href="/login"
              className="text-sm font-semibold text-indigo-400 hover:text-indigo-350"
            >
              Go to Login Page
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VerifyEmail() {
  return (
    <div className="flex min-h-screen flex-col bg-black text-white">
      <Navbar />
      <div className="flex flex-1 items-center justify-center px-4 py-16 sm:px-6 lg:px-8">
        <Suspense fallback={<div className="text-center py-10">Loading email verification...</div>}>
          <VerifyEmailForm />
        </Suspense>
      </div>
      <Footer />
    </div>
  );
}
