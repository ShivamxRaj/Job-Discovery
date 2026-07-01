"use client";

import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Check } from "lucide-react";
import Link from "next/link";

export default function Pricing() {
  const plans = [
    {
      name: "Starter",
      price: "$0",
      description: "Perfect for students and recent grads starting their job search.",
      features: [
        "Upload up to 3 resume versions",
        "AI Resume parsing & skill normalization",
        "Basic ATS scoring",
        "10 AI job matches per month",
        "Standard search filters"
      ],
      cta: "Get Started Free",
      popular: false
    },
    {
      name: "Professional",
      price: "$19",
      description: "For active job seekers who want to speed up interviews.",
      features: [
        "Unlimited resume version uploads",
        "Advanced ATS scoring & line suggestions",
        "Unlimited AI job matches & vector scoring",
        "OpenAI Match explanations",
        "AI Cover letter & HR outreach generators",
        "Stateful Kanban application tracker"
      ],
      cta: "Upgrade to Pro",
      popular: true
    },
    {
      name: "Enterprise",
      price: "$49",
      description: "For professional recruiters and staffing agencies.",
      features: [
        "Everything in Professional",
        "Bulk resume parsing & embedding generation",
        "Custom rule engine configurations",
        "Dedicated account support",
        "API access to recommendations feed",
        "Daily automated job digest alerts"
      ],
      cta: "Contact Sales",
      popular: false
    }
  ];

  return (
    <div className="flex min-h-screen flex-col bg-black text-white">
      <Navbar />
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
          Simple, Transparent Pricing
        </h1>
        <p className="mt-4 text-zinc-400 max-w-xl mx-auto">
          Choose the plan that fits your job search needs. No hidden fees. Cancel anytime.
        </p>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-left max-w-6xl mx-auto">
          {plans.map((plan, idx) => (
            <div
              key={idx}
              className={`rounded-2xl border p-8 flex flex-col justify-between transition-all ${
                plan.popular
                  ? "border-indigo-500 bg-indigo-950/10 shadow-[0_0_25px_rgba(79,70,229,0.15)] scale-105"
                  : "border-zinc-800 bg-zinc-950"
              }`}
            >
              <div>
                <div className="flex justify-between items-center">
                  <h3 className="text-xl font-bold text-white">{plan.name}</h3>
                  {plan.popular && (
                    <span className="rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">
                      Most Popular
                    </span>
                  )}
                </div>
                <div className="mt-4 flex items-baseline text-white">
                  <span className="text-4xl font-extrabold tracking-tight">{plan.price}</span>
                  <span className="ml-1 text-sm font-semibold text-zinc-400">/month</span>
                </div>
                <p className="mt-3 text-sm text-zinc-400 leading-relaxed">{plan.description}</p>

                <ul className="mt-6 space-y-3">
                  {plan.features.map((feat, fIdx) => (
                    <li key={fIdx} className="flex items-start gap-2 text-sm text-zinc-300">
                      <Check className="h-4.5 w-4.5 text-indigo-400 shrink-0 mt-0.5" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-8">
                <Link
                  href={plan.name === "Enterprise" ? "mailto:sales@jobdiscovery.com" : "/register"}
                  className={`block w-full text-center rounded-xl py-3 text-sm font-semibold transition-all ${
                    plan.popular
                      ? "bg-indigo-600 text-white hover:bg-indigo-500 hover:shadow-[0_0_15px_rgba(79,70,229,0.3)]"
                      : "bg-zinc-900 border border-zinc-800 text-zinc-300 hover:bg-zinc-800"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
      <Footer />
    </div>
  );
}
