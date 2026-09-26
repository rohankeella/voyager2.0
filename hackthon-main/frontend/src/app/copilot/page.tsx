"use client";

/**
 * DTO-P3 Phase 3 — Tripartite AI Co-Pilot.
 *
 * Left    → conversational chat driving Planner→Executor→Supervisor
 * Center  → interactive 3D globe rendering the DAG (arcs + polylines + markers)
 * Right   → SuperTrip preview with HITL "Review & Approve" cards
 *
 * On desktop the three panes share one viewport (no page scroll); the chat
 * thread and itinerary scroll inside their own panes. Below `lg` they stack.
 * Clicking a node in either the preview or the globe focuses it in the other.
 * When the user is signed in, the plan is auto-persisted for the dashboard.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, ArrowLeft, LogIn } from "lucide-react";
import CopilotChat from "@/components/copilot/copilot-chat";
import SuperTripPreview, { PreviewEmpty, PreviewSkeleton } from "@/components/copilot/super-trip-preview";
import { getStoredUser, type PlanTripResponse, type ApiUser } from "@/lib/api";

// Globe is client-only (MapLibre depends on window/WebGL) — dynamic import.
const SuperTripGlobe = dynamic(() => import("@/components/copilot/super-trip-globe"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center rounded-2xl bg-[radial-gradient(110%_85%_at_50%_42%,#0f3b3d_0%,#082830_42%,#031017_100%)]">
      <span className="text-xs text-teal-50/70">Loading globe…</span>
    </div>
  ),
});

const SAMPLE_PROMPTS = [
  "5-day Paris trip from Bangalore, $2500 budget, love art and food",
  "Weekend Goa getaway from Mumbai, $600 for two travelers, beaches and seafood",
  "10 days across Japan (Tokyo + Kyoto) from Delhi, $4000, temples & ramen",
  "3-day Jaipur trip from Bangalore, $500, palaces and Rajasthani cuisine",
];

type PlanResult = PlanTripResponse & { prompt: string };

export default function CopilotPage() {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [planResult, setPlanResult] = useState<PlanResult | null>(null);
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);
  const [planning, setPlanning] = useState(false);

  useEffect(() => {
    // localStorage is client-only; reading it during render would mismatch the server HTML.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUser(getStoredUser());
  }, []);

  // Reset focus when a new plan arrives so the globe re-fits from scratch.
  const handlePlan = (result: PlanResult) => {
    setPlanResult(result);
    setFocusNodeId(null);
  };

  const trip = planResult?.trip ?? null;

  return (
    <div className="flex min-h-dvh flex-col bg-background lg:h-dvh lg:overflow-hidden">
      <header className="shrink-0 border-b border-slate-200/80 bg-white">
        <div className="flex h-14 items-center justify-between gap-4 px-3 lg:px-4">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              href="/dashboard"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition-colors duration-150 hover:bg-slate-100 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              aria-label="Back to dashboard"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-white">
              <Sparkles className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <h1 className="text-sm font-semibold leading-tight text-slate-900">AI Trip Co-Pilot</h1>
              <p className="truncate text-xs text-slate-500">
                Multi-agent DAG planner · 3D globe · Powered by Groq
              </p>
            </div>
          </div>
          {user ? (
            <div className="hidden shrink-0 text-xs text-slate-500 sm:block">
              Signed in as <span className="font-semibold text-slate-900">{user.full_name}</span>
            </div>
          ) : (
            <Link
              href="/login"
              className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-primary px-3.5 py-1.5 text-xs font-semibold text-white transition-colors duration-150 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2"
            >
              <LogIn className="h-3.5 w-3.5" /> Sign in to save
            </Link>
          )}
        </div>
      </header>

      <main className="grid flex-1 gap-3 p-3 lg:min-h-0 lg:grid-cols-[minmax(300px,340px)_minmax(0,1fr)_minmax(340px,400px)] lg:grid-rows-[minmax(0,1fr)] xl:grid-cols-[360px_minmax(0,1fr)_420px]">
        <section aria-label="Chat with the co-pilot" className="h-[72dvh] min-h-[28rem] lg:h-auto lg:min-h-0">
          <CopilotChat
            samplePrompts={SAMPLE_PROMPTS}
            hasPlan={!!trip}
            onPlan={handlePlan}
            onBusyChange={setPlanning}
          />
        </section>

        <section aria-label="Route globe" className="h-[60dvh] min-h-[22rem] lg:h-auto lg:min-h-0">
          <SuperTripGlobe trip={trip} planning={planning} focusNodeId={focusNodeId} onNodeClick={setFocusNodeId} />
        </section>

        <section aria-label="Itinerary" className="h-[85dvh] min-h-[28rem] lg:h-auto lg:min-h-0">
          {planning ? (
            <PreviewSkeleton />
          ) : planResult?.trip ? (
            <SuperTripPreview
              trip={planResult.trip}
              persistedId={planResult.persisted_id}
              hitlRequired={planResult.hitl_required}
              hitlReason={planResult.hitl_reason}
              warnings={planResult.warnings}
              onFocusNode={setFocusNodeId}
              focusNodeId={focusNodeId}
            />
          ) : (
            <PreviewEmpty />
          )}
        </section>
      </main>
    </div>
  );
}
