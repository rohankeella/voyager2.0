"use client";

import {
  Plane,
  Hotel as HotelIcon,
  Car,
  Utensils,
  Compass,
  MapPin,
  UserCheck,
  Sparkles,
  Clock,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { TripNode, SuperTripNodeType } from "@/lib/api";

type Props = {
  node: TripNode;
  index: number;
  onApprove?: (nodeId: string) => void;
  approved?: boolean;
};

const TYPE_META: Record<
  SuperTripNodeType,
  { label: string; icon: React.ComponentType<{ className?: string }>; accent: string; bg: string }
> = {
  amadeus_flight_order: { label: "Flight", icon: Plane, accent: "text-sky-700", bg: "bg-sky-50" },
  amadeus_flight_offer: { label: "Flight (offer)", icon: Plane, accent: "text-sky-700", bg: "bg-sky-50" },
  amadeus_hotel_booking: { label: "Hotel", icon: HotelIcon, accent: "text-amber-700", bg: "bg-amber-50" },
  amadeus_hotel_offer: { label: "Hotel (offer)", icon: HotelIcon, accent: "text-amber-700", bg: "bg-amber-50" },
  otp_ground_transfer: { label: "Transfer", icon: Car, accent: "text-slate-700", bg: "bg-slate-50" },
  activity: { label: "Activity", icon: Compass, accent: "text-emerald-700", bg: "bg-emerald-50" },
  meal: { label: "Meal", icon: Utensils, accent: "text-rose-700", bg: "bg-rose-50" },
  guide_session: { label: "Guide", icon: UserCheck, accent: "text-indigo-700", bg: "bg-indigo-50" },
  custom: { label: "Custom", icon: Sparkles, accent: "text-purple-700", bg: "bg-purple-50" },
};

function fmtDT(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function fmtDuration(start?: string | null, end?: string | null): string | null {
  if (!start || !end) return null;
  try {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms <= 0) return null;
    const mins = Math.round(ms / 60000);
    if (mins < 60) return `${mins}m`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m ? `${h}h ${m}m` : `${h}h`;
  } catch {
    return null;
  }
}

export default function TripNodeCard({ node, index, onApprove, approved }: Props) {
  const meta = TYPE_META[node.type] ?? TYPE_META.custom;
  const Icon = meta.icon;
  const cost = node.financials.cost_usd;
  const start = node.execution_data.start_time;
  const end = node.execution_data.end_time;
  const duration = fmtDuration(start, end);
  const loc = node.execution_data.location_label;
  const pnr = node.execution_data.pnr_number;

  const needsApproval = node.requires_approval || cost >= 500;

  return (
    <div
      className={cn(
        "rounded-2xl border bg-white p-4 shadow-sm transition-colors",
        approved
          ? "border-emerald-200 ring-1 ring-emerald-100"
          : needsApproval
            ? "border-amber-200 ring-1 ring-amber-100"
            : "border-gray-100",
      )}
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
            meta.bg,
            meta.accent,
          )}
        >
          <Icon className="h-4 w-4" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className={cn("text-[10px] font-semibold uppercase tracking-wider", meta.accent)}>
                  {meta.label}
                </span>
                <span className="text-[10px] text-gray-400">·</span>
                <span className="font-mono text-[10px] text-gray-400">{node.node_id}</span>
                <span className="text-[10px] text-gray-400">·</span>
                <span className="text-[10px] text-gray-400">step {index + 1}</span>
              </div>
              <h3 className="mt-0.5 truncate text-sm font-semibold text-dark">
                {node.title || meta.label}
              </h3>
            </div>
            <div className="text-right">
              <div className="text-sm font-bold text-dark">${cost.toFixed(0)}</div>
              {needsApproval && !approved && (
                <div className="text-[10px] font-semibold uppercase tracking-wider text-amber-600">
                  Approval
                </div>
              )}
              {approved && (
                <div className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600">
                  Approved
                </div>
              )}
            </div>
          </div>

          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
            {start && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {fmtDT(start)}
                {duration && <span className="ml-1 text-gray-400">· {duration}</span>}
              </span>
            )}
            {loc && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {loc}
              </span>
            )}
            {pnr && (
              <span className="rounded bg-slate-100 px-1.5 font-mono text-[10px] text-slate-600">
                PNR {pnr}
              </span>
            )}
          </div>

          {node.description && (
            <p className="mt-2 line-clamp-2 text-xs text-gray-500">{node.description}</p>
          )}

          {node.depends_on.length > 0 && (
            <div className="mt-2 text-[10px] text-gray-400">
              Depends on: {node.depends_on.map((d) => d.split("-")[1]).join(", ")}
            </div>
          )}

          {needsApproval && !approved && onApprove && (
            <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 p-2.5 text-xs">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
              <div className="flex-1 text-amber-800">
                High-value booking — needs your approval before we route payment.
              </div>
              <button
                onClick={() => onApprove(node.node_id)}
                className="rounded-lg bg-amber-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-amber-700"
              >
                Approve
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
