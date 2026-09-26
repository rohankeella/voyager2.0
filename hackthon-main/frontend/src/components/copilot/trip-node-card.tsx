"use client";

import {
  Plane,
  Hotel as HotelIcon,
  Car,
  Utensils,
  Compass,
  UserCheck,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { TripNode, SuperTripNodeType } from "@/lib/api";

type Props = {
  node: TripNode;
  onApprove?: (nodeId: string) => void;
  approved?: boolean;
  focused?: boolean;
  onFocus?: (nodeId: string) => void;
};

const TYPE_META: Record<
  SuperTripNodeType,
  { label: string; icon: React.ComponentType<{ className?: string }>; accent: string; bg: string }
> = {
  amadeus_flight_order: { label: "Flight", icon: Plane, accent: "text-sky-700", bg: "bg-sky-50" },
  amadeus_flight_offer: { label: "Flight (offer)", icon: Plane, accent: "text-sky-700", bg: "bg-sky-50" },
  amadeus_hotel_booking: { label: "Hotel", icon: HotelIcon, accent: "text-amber-700", bg: "bg-amber-50" },
  amadeus_hotel_offer: { label: "Hotel (offer)", icon: HotelIcon, accent: "text-amber-700", bg: "bg-amber-50" },
  otp_ground_transfer: { label: "Transfer", icon: Car, accent: "text-slate-700", bg: "bg-slate-100" },
  activity: { label: "Activity", icon: Compass, accent: "text-emerald-700", bg: "bg-emerald-50" },
  meal: { label: "Meal", icon: Utensils, accent: "text-rose-700", bg: "bg-rose-50" },
  guide_session: { label: "Guide", icon: UserCheck, accent: "text-indigo-700", bg: "bg-indigo-50" },
  custom: { label: "Custom", icon: Sparkles, accent: "text-purple-700", bg: "bg-purple-50" },
};

function fmtTime(iso?: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function fmtDuration(start?: string | null, end?: string | null): string | null {
  if (!start || !end) return null;
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (!(ms > 0)) return null;
  const mins = Math.round(ms / 60000);
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  if (h >= 24) return `${Math.round(h / 24)}d`;
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export default function TripNodeCard({ node, onApprove, approved, focused, onFocus }: Props) {
  const meta = TYPE_META[node.type] ?? TYPE_META.custom;
  const Icon = meta.icon;
  const cost = node.financials.cost_usd;
  const time = fmtTime(node.execution_data.start_time);
  const duration = fmtDuration(node.execution_data.start_time, node.execution_data.end_time);
  // Transfers without a resolved endpoint arrive as "Paris → "; drop the dangling arrow.
  const loc = node.execution_data.location_label?.replace(/\s*→\s*$/, "");
  const pnr = node.execution_data.pnr_number;
  const deps = node.depends_on.map((d) => d.split("-")[1]).join(", ");

  const needsApproval = node.requires_approval || cost >= 500;
  const awaitingApproval = needsApproval && !approved && !!onApprove;

  return (
    <div
      className={cn(
        "rounded-xl transition-colors duration-150",
        focused ? "bg-teal-50 ring-1 ring-inset ring-teal-600/25" : awaitingApproval ? "bg-amber-50/40" : "hover:bg-slate-50",
      )}
    >
      <button
        type="button"
        onClick={() => onFocus?.(node.node_id)}
        disabled={!onFocus}
        aria-pressed={onFocus ? !!focused : undefined}
        title={`${node.node_id}${deps ? ` · after ${deps}` : ""} — show on globe`}
        className="flex w-full items-start gap-3 rounded-xl px-2 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-default"
      >
        <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", meta.bg, meta.accent)}>
          <Icon className="h-4 w-4" />
        </span>

        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="truncate text-sm font-semibold text-slate-900">{node.title || meta.label}</span>
            <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-900">${cost.toFixed(0)}</span>
          </span>

          <span className="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-slate-500">
            <span className={cn("shrink-0 font-medium", meta.accent)}>{meta.label}</span>
            {time && (
              <>
                <span aria-hidden>·</span>
                <span className="shrink-0 tabular-nums">
                  {time}
                  {duration && ` · ${duration}`}
                </span>
              </>
            )}
            {loc && (
              <>
                <span aria-hidden>·</span>
                <span className="truncate">{loc}</span>
              </>
            )}
          </span>

          {(node.description || pnr || (needsApproval && approved)) && (
            <span className="mt-1 flex min-w-0 items-center gap-2 text-xs text-slate-500">
              {needsApproval && approved && (
                <span className="inline-flex shrink-0 items-center gap-1 font-medium text-emerald-700">
                  <CheckCircle2 className="h-3 w-3" /> Approved
                </span>
              )}
              {pnr && (
                <span className="shrink-0 rounded bg-slate-100 px-1.5 font-mono text-[11px] text-slate-600">
                  PNR {pnr}
                </span>
              )}
              {node.description && <span className="truncate">{node.description}</span>}
            </span>
          )}
        </span>
      </button>

      {awaitingApproval && (
        <div className="-mt-1 flex items-center gap-2 pb-2.5 pl-[3.25rem] pr-2 text-xs">
          <p className="flex-1 leading-snug text-amber-900">
            High-value booking — needs your approval before we route payment.
          </p>
          <button
            type="button"
            onClick={() => onApprove(node.node_id)}
            className="shrink-0 rounded-lg bg-amber-700 px-3 py-1.5 font-semibold text-white transition-colors duration-150 hover:bg-amber-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600/50 focus-visible:ring-offset-1"
          >
            Approve
          </button>
        </div>
      )}
    </div>
  );
}
