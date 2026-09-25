"use client";

/**
 * DTO-P3 Phase 4 — Operator Command Center.
 *
 * Bird's-eye view for tour operators: live Gantt, vendor status matrix,
 * disruption queue, and a lights summary. Polls /api/operator/command-center
 * every 30s (Phase 5 will upgrade to SSE push).
 *
 * Auth: server enforces operator/admin role. If a traveler hits this route
 * they'll get a 403 and see the empty state with a link back home.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw, ShieldAlert } from "lucide-react";
import LiveGantt from "@/components/operator-center/live-gantt";
import VendorMatrix from "@/components/operator-center/vendor-matrix";
import DisruptionQueue from "@/components/operator-center/disruption-queue";
import LightsSummary from "@/components/operator-center/lights-summary";
import TriggerDisruptionDialog from "@/components/operator-center/trigger-disruption-dialog";
import {
  operatorApi,
  ApiError,
  type CommandCenterResponse,
  type GanttTrip,
  type GanttNode,
  subscribeToUpdates,
} from "@/lib/api";

const REFRESH_MS = 30_000;

export default function CommandCenterPage() {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<{ status?: number; message: string } | null>(null);
  const [triggerContext, setTriggerContext] = useState<{ trip: GanttTrip; node: GanttNode } | null>(null);

  const load = useCallback(
    async (mode: "initial" | "refresh" = "initial") => {
      if (mode === "initial") setLoading(true);
      else setRefreshing(true);
      try {
        const res = await operatorApi.commandCenter();
        setData(res);
        setError(null);
      } catch (e) {
        if (e instanceof ApiError) {
          setError({ status: e.status, message: e.message });
        } else if (e instanceof Error) {
          setError({ message: e.message });
        } else {
          setError({ message: "Failed to load command center" });
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    load("initial");
    const iv = setInterval(() => load("refresh"), REFRESH_MS);
    return () => clearInterval(iv);
  }, [load]);

  // SSE — refresh instantly whenever the realtime bus publishes anything.
  useEffect(() => {
    const off = subscribeToUpdates(() => {
      load("refresh");
    });
    return off;
  }, [load]);

  if (loading && !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-sm text-gray-500">Loading command center…</div>
      </div>
    );
  }

  if (error) {
    const denied = error.status === 401 || error.status === 403;
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md rounded-3xl border border-gray-100 bg-white p-8 text-center shadow-sm">
          <ShieldAlert className="mx-auto h-10 w-10 text-red-400" />
          <h1 className="mt-4 text-lg font-bold text-dark">
            {denied ? "Operator access required" : "Command center offline"}
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            {denied
              ? "Sign in with an operator or admin account to view the Fleet Gantt."
              : error.message}
          </p>
          <Link
            href={denied ? "/login" : "/dashboard"}
            className="mt-6 inline-block rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
          >
            {denied ? "Go to sign in" : "Back to dashboard"}
          </Link>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-100 bg-white">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-primary">
              Operator Command Center
            </p>
            <h1 className="text-lg font-bold text-dark">Fleet situational awareness</h1>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-gray-500">
            <span>
              Last update:{" "}
              <time className="font-mono text-dark" dateTime={data.generated_at}>
                {new Date(data.generated_at).toLocaleTimeString()}
              </time>
            </span>
            <button
              onClick={() => load("refresh")}
              disabled={refreshing}
              className="flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1 hover:border-primary hover:text-primary disabled:opacity-40"
            >
              <RefreshCw className={refreshing ? "h-3 w-3 animate-spin" : "h-3 w-3"} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] space-y-4 p-4 lg:p-6">
        <LightsSummary summary={data.lights_summary} activeTripCount={data.active_trip_count} />

        <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="min-h-[400px]">
            <LiveGantt
              trips={data.active_trips}
              onTriggerDisruption={(trip, node) => setTriggerContext({ trip, node })}
            />
          </div>
          <div className="grid min-h-[400px] gap-4 lg:grid-rows-2">
            <VendorMatrix rows={data.vendor_matrix} />
            <DisruptionQueue
              items={data.disruption_queue}
              onMitigated={() => load("refresh")}
            />
          </div>
        </div>
      </main>

      {triggerContext && (
        <TriggerDisruptionDialog
          trip={triggerContext.trip}
          node={triggerContext.node}
          onClose={() => setTriggerContext(null)}
          onCreated={() => load("refresh")}
        />
      )}
    </div>
  );
}
