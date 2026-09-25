"use client";

/**
 * DTO-P3 Phase 4 — Live Gantt Matrix.
 *
 * Per PRD § "Global Fleet Tracking and Gantt Visualization":
 *   - One horizontal track per active traveler / trip
 *   - Every DAG node → coloured duration block
 *   - Traffic-light: green (nominal) / yellow (drift) / red (conflict)
 *   - Vertical "now" line advances in real time so operators can see
 *     which trips are underway.
 *
 * Implemented as a CSS-grid Gantt to avoid pulling in a heavy chart lib —
 * blocks are absolutely positioned based on percentage offsets across the
 * global time window. Clicking a block emits `onFocusNode`.
 */

import { useMemo, useState, useEffect } from "react";
import { Plane, Hotel as HotelIcon, Car, Utensils, Compass, UserCheck, Sparkles } from "lucide-react";
import type { GanttTrip, GanttNode, SuperTripNodeType, StatusLight } from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  trips: GanttTrip[];
  onFocusNode?: (tripId: string, nodeId: string) => void;
  onTriggerDisruption?: (trip: GanttTrip, node: GanttNode) => void;
};

const NODE_ICON: Record<SuperTripNodeType, React.ComponentType<{ className?: string }>> = {
  amadeus_flight_order: Plane,
  amadeus_flight_offer: Plane,
  amadeus_hotel_booking: HotelIcon,
  amadeus_hotel_offer: HotelIcon,
  otp_ground_transfer: Car,
  activity: Compass,
  meal: Utensils,
  guide_session: UserCheck,
  custom: Sparkles,
};

const LIGHT_BG: Record<StatusLight, string> = {
  green: "bg-emerald-500/85 hover:bg-emerald-500",
  yellow: "bg-amber-500/85 hover:bg-amber-500",
  red: "bg-red-500/90 hover:bg-red-500",
  grey: "bg-slate-400/70 hover:bg-slate-400",
};

const LIGHT_LABEL: Record<StatusLight, string> = {
  green: "On schedule",
  yellow: "Warning",
  red: "Critical",
  grey: "Complete",
};

function parse(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : null;
}

function fmtDayLabel(t: number): string {
  const d = new Date(t);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function computeWindow(trips: GanttTrip[]): { start: number; end: number } | null {
  let min = Infinity;
  let max = -Infinity;
  for (const trip of trips) {
    for (const n of trip.nodes) {
      const s = parse(n.start_time);
      const e = parse(n.end_time);
      if (s !== null && s < min) min = s;
      if (e !== null && e > max) max = e;
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max) || min >= max) return null;
  // Add 4% padding on each side.
  const span = max - min;
  return { start: min - span * 0.02, end: max + span * 0.02 };
}

function dayTicks(win: { start: number; end: number }): number[] {
  const ticks: number[] = [];
  // 6 evenly-spaced tick marks so the axis is legible on any span.
  for (let i = 0; i <= 5; i++) {
    ticks.push(win.start + ((win.end - win.start) * i) / 5);
  }
  return ticks;
}

export default function LiveGantt({ trips, onFocusNode, onTriggerDisruption }: Props) {
  const win = useMemo(() => computeWindow(trips), [trips]);
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    const iv = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(iv);
  }, []);

  if (!win || trips.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-3xl border border-gray-100 bg-white p-8 text-center">
        <Plane className="h-8 w-8 text-gray-300" />
        <p className="mt-3 text-sm font-semibold text-dark">No active trips yet</p>
        <p className="mt-1 max-w-xs text-xs text-gray-500">
          Travellers whose plans are pending review, approved, or in progress will appear here as tracks on the timeline.
        </p>
      </div>
    );
  }

  const span = win.end - win.start;
  const nowPct = Math.max(-2, Math.min(102, ((now - win.start) / span) * 100));
  const nowVisible = nowPct >= 0 && nowPct <= 100;
  const ticks = dayTicks(win);

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
      {/* header */}
      <div className="flex items-center justify-between gap-3 border-b border-gray-100 p-4">
        <div>
          <h3 className="text-sm font-bold text-dark">Fleet Gantt</h3>
          <p className="text-[11px] text-gray-500">
            {trips.length} active trip{trips.length === 1 ? "" : "s"} · updates every 30s
          </p>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-gray-500">
          {(["green", "yellow", "red", "grey"] as StatusLight[]).map((l) => (
            <span key={l} className="flex items-center gap-1">
              <span className={cn("h-2.5 w-2.5 rounded-sm", LIGHT_BG[l])} />
              {LIGHT_LABEL[l]}
            </span>
          ))}
        </div>
      </div>

      {/* body */}
      <div className="flex-1 overflow-auto">
        <div className="min-w-[720px]">
          {/* time axis */}
          <div className="sticky top-0 z-10 flex bg-white/95 backdrop-blur">
            <div className="w-56 shrink-0 border-b border-r border-gray-100 p-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
              Traveler / Trip
            </div>
            <div className="relative flex-1 border-b border-gray-100">
              {ticks.map((t, i) => (
                <div
                  key={i}
                  className="absolute top-0 -translate-x-1/2 border-l border-dashed border-gray-100 pl-1 pr-1 text-[10px] text-gray-400"
                  style={{ left: `${((t - win.start) / span) * 100}%`, height: "100%" }}
                >
                  <span className="inline-block pt-1">{fmtDayLabel(t)}</span>
                </div>
              ))}
              {nowVisible && (
                <div
                  className="pointer-events-none absolute top-0 z-20 h-full w-px bg-primary/70"
                  style={{ left: `${nowPct}%` }}
                >
                  <span className="absolute -top-0.5 -translate-x-1/2 rounded bg-primary px-1 text-[9px] font-semibold text-white">
                    NOW
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* rows */}
          {trips.map((trip) => (
            <TripRow
              key={trip.super_trip_id}
              trip={trip}
              windowStart={win.start}
              windowSpan={span}
              nowPct={nowVisible ? nowPct : null}
              onFocusNode={onFocusNode}
              onTriggerDisruption={onTriggerDisruption}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function TripRow({
  trip,
  windowStart,
  windowSpan,
  nowPct,
  onFocusNode,
  onTriggerDisruption,
}: {
  trip: GanttTrip;
  windowStart: number;
  windowSpan: number;
  nowPct: number | null;
  onFocusNode?: (tripId: string, nodeId: string) => void;
  onTriggerDisruption?: (trip: GanttTrip, node: GanttNode) => void;
}) {
  const [hover, setHover] = useState<string | null>(null);

  const lightBadge = (
    <div className="flex gap-1 text-[10px]">
      {(["red", "yellow", "green"] as StatusLight[]).map((l) => {
        const count = trip.lights[l] ?? 0;
        if (!count) return null;
        return (
          <span
            key={l}
            className={cn("rounded px-1 py-0.5 font-mono text-white", LIGHT_BG[l].split(" ")[0])}
          >
            {count}
          </span>
        );
      })}
    </div>
  );

  return (
    <div className="flex border-b border-gray-100 last:border-0">
      <div className="w-56 shrink-0 border-r border-gray-100 p-2">
        <div className="text-xs font-semibold text-dark truncate" title={trip.title}>
          {trip.title.replace(/·.*/, "").trim() || trip.home_location || "Trip"}
        </div>
        <div className="mt-0.5 flex items-center justify-between gap-2 text-[10px] text-gray-500">
          <span className="font-mono truncate">{trip.super_trip_id}</span>
          {lightBadge}
        </div>
        <div className="mt-0.5 text-[10px] text-gray-400">
          ${trip.total_cost_usd.toFixed(0)} · {trip.node_count} nodes
        </div>
      </div>

      <div className="relative flex-1" style={{ height: "56px" }}>
        {nowPct !== null && (
          <div
            className="pointer-events-none absolute top-0 z-10 h-full w-px bg-primary/70"
            style={{ left: `${nowPct}%` }}
          />
        )}
        {trip.nodes.map((node) => {
          const s = parse(node.start_time);
          const e = parse(node.end_time);
          if (s === null || e === null) return null;
          const left = ((s - windowStart) / windowSpan) * 100;
          const width = Math.max(0.6, ((e - s) / windowSpan) * 100);
          const light = node.status_light;
          const Icon = NODE_ICON[node.type] ?? Sparkles;
          const isHover = hover === node.node_id;

          return (
            <button
              key={node.node_id}
              onClick={() => {
                onFocusNode?.(trip.super_trip_id, node.node_id);
                onTriggerDisruption?.(trip, node);
              }}
              onMouseEnter={() => setHover(node.node_id)}
              onMouseLeave={() => setHover(null)}
              className={cn(
                "absolute top-1/2 flex -translate-y-1/2 items-center gap-1 overflow-hidden rounded-md px-1.5 text-[10px] font-medium text-white shadow-sm outline-none transition-all",
                LIGHT_BG[light],
                isHover && "ring-2 ring-primary/60 z-30",
              )}
              style={{ left: `${left}%`, width: `${width}%`, height: "28px" }}
              title={onTriggerDisruption ? `${node.title} · click to trigger disruption` : `${node.title} · ${node.status_reason}`}
            >
              <Icon className="h-3 w-3 shrink-0" />
              <span className="truncate">{node.title}</span>
              {isHover && (
                <span className="ml-auto shrink-0 rounded bg-black/25 px-1 text-[9px]">
                  ${node.cost_usd.toFixed(0)}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
