"use client";

/**
 * DTO-P3 Phase 3 — Tripartite AI Co-Pilot.
 *
 * Left    → conversational chat driving Planner→Executor→Supervisor
 * Center  → interactive 3D globe rendering the DAG (arcs + polylines + markers)
 * Right   → SuperTrip preview with HITL "Review & Approve" cards
 *
 * All three panes stay synchronized: chat generates a plan → globe pans over
 * it → clicking a node in either the preview or the globe focuses it in the
 * other. When the user is signed in, the plan is auto-persisted for the
 * dashboard + operator Gantt (Phase 4).
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, ArrowLeft, LogIn, Globe as GlobeIcon } from "lucide-react";
import CopilotChat from "@/components/copilot/copilot-chat";
import SuperTripPreview from "@/components/copilot/super-trip-preview";
import { getStoredUser, type PlanTripResponse, type ApiUser, type SuperTripDetail } from "@/lib/api";

// Globe is client-only (MapLibre depends on window/WebGL) — dynamic import.
const SuperTripGlobe = dynamic(() => import("@/components/copilot/super-trip-globe"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center rounded-3xl border border-gray-100 bg-slate-950 text-white/70">
      <div className="flex flex-col items-center gap-2">
        <GlobeIcon className="h-6 w-6 animate-pulse" />
        <span className="text-xs">Loading globe…</span>
      </div>
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

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  // Reset focus when a new plan arrives so the globe re-fits from scratch.
  useEffect(() => {
    setFocusNodeId(null);
  }, [planResult?.trip?.super_trip_id]);

  const handleApproved = (_record: SuperTripDetail) => {
    // Approval is confirmed inside SuperTripPreview; nothing extra to do here yet.
  };

  const trip = planResult?.trip ?? null;

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* header */}
      <header className="border-b border-gray-100 bg-white">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:border-primary hover:text-primary"
              aria-label="Back to dashboard"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Sparkles className="h-4 w-4" />
              </span>
              <div>
                <h1 className="text-sm font-bold text-dark">AI Trip Co-Pilot</h1>
                <p className="text-[11px] text-gray-500">
                  Multi-agent DAG planner · 3D globe · Powered by Gemini
                </p>
              </div>
            </div>
          </div>
          <div>
            {user ? (
              <div className="text-xs text-gray-500">
                Signed in as <span className="font-semibold text-dark">{user.full_name}</span>
              </div>
            ) : (
              <Link
                href="/login"
                className="inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90"
              >
                <LogIn className="h-3 w-3" /> Sign in to save
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* tripartite layout */}
      <main className="mx-auto grid w-full max-w-[1600px] flex-1 gap-4 p-4 lg:grid-cols-[minmax(260px,320px)_minmax(0,1fr)_minmax(300px,420px)] lg:p-5">
        {/* Chat */}
        <div className="min-h-[420px] lg:min-h-[calc(100vh-6rem)]">
          <CopilotChat
            samplePrompts={SAMPLE_PROMPTS}
            hasPlan={!!trip}
            onPlan={setPlanResult}
          />
        </div>

        {/* Globe */}
        <div className="min-h-[420px] lg:min-h-[calc(100vh-6rem)]">
          {trip ? (
            <SuperTripGlobe
              trip={trip}
              focusNodeId={focusNodeId}
              onNodeClick={setFocusNodeId}
            />
          ) : (
            <GlobeEmpty />
          )}
        </div>

        {/* Preview */}
        <div className="min-h-[420px] lg:min-h-[calc(100vh-6rem)]">
          {planResult?.trip ? (
            <SuperTripPreview
              trip={planResult.trip}
              persistedId={planResult.persisted_id}
              hitlRequired={planResult.hitl_required}
              hitlReason={planResult.hitl_reason}
              warnings={planResult.warnings}
              onApproved={handleApproved}
              onFocusNode={setFocusNodeId}
              focusNodeId={focusNodeId}
            />
          ) : (
            <PreviewEmpty />
          )}
        </div>
      </main>
    </div>
  );
}

function GlobeEmpty() {
  return (
    <div className="flex h-full flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed border-gray-200 bg-white p-8 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
        <GlobeIcon className="h-6 w-6" />
      </span>
      <h2 className="mt-4 text-base font-bold text-dark">Globe will render your trip here</h2>
      <p className="mt-2 max-w-sm text-xs text-gray-500">
        Once the Planner generates a DAG, this pane visualizes flight arcs as great-circles,
        ground transfers as polylines, and hotels/activities as coloured markers on a real 3D globe.
      </p>
    </div>
  );
}

function PreviewEmpty() {
  return (
    <div className="flex h-full flex-col items-center justify-center rounded-3xl border-2 border-dashed border-gray-200 bg-white p-8 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Sparkles className="h-6 w-6" />
      </span>
      <h2 className="mt-4 text-base font-bold text-dark">Ask the co-pilot to plan a trip</h2>
      <p className="mt-2 max-w-sm text-xs text-gray-500">
        Describe your ideal getaway on the left. High-value bookings surface here as Review & Approve cards.
      </p>
      <div className="mt-6 grid grid-cols-3 gap-2 text-[10px] text-gray-400">
        <StepBadge label="1 · Planner" />
        <StepBadge label="2 · Executor" />
        <StepBadge label="3 · Supervisor" />
      </div>
    </div>
  );
}

function StepBadge({ label }: { label: string }) {
  return <div className="rounded-full border border-gray-200 px-2 py-1 font-mono">{label}</div>;
}
