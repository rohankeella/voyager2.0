"use client";

/**
 * DTO-P3 Phase 5 — Disruption Queue with recovery plan cards.
 *
 * Each open disruption expands into 3 candidate plans (fastest / cheapest /
 * least_impact). Clicking a plan calls the Cascade Protocol's apply endpoint
 * which rewrites the DAG and closes the disruption.
 */

import { useState } from "react";
import {
  AlertTriangle,
  Zap,
  Clock,
  DollarSign,
  CheckCircle2,
  Loader2,
  XCircle,
  Scissors,
  Wind,
} from "lucide-react";
import {
  disruptionsApi,
  ApiError,
  type DisruptionQueueItem,
  type RecoveryPlan,
  type SuperDisruptionKind,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  items: DisruptionQueueItem[];
  onMitigated?: (superTripId: string, disruptionId: string, planId: string) => void;
};

const KIND_META: Record<
  SuperDisruptionKind,
  { label: string; Icon: React.ComponentType<{ className?: string }>; tone: string }
> = {
  delay: { label: "Delay", Icon: Clock, tone: "bg-amber-50 text-amber-700 border-amber-100" },
  cancellation: { label: "Cancellation", Icon: XCircle, tone: "bg-red-50 text-red-700 border-red-100" },
  weather: { label: "Weather", Icon: Wind, tone: "bg-sky-50 text-sky-700 border-sky-100" },
  overbooked: { label: "Overbooked", Icon: AlertTriangle, tone: "bg-rose-50 text-rose-700 border-rose-100" },
  capacity: { label: "Capacity", Icon: AlertTriangle, tone: "bg-orange-50 text-orange-700 border-orange-100" },
  other: { label: "Event", Icon: AlertTriangle, tone: "bg-slate-50 text-slate-700 border-slate-100" },
};

export default function DisruptionQueue({ items, onMitigated }: Props) {
  const count = items.length;
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 p-4">
        <div>
          <h3 className="text-sm font-bold text-dark">Disruption Queue</h3>
          <p className="text-[11px] text-gray-500">
            {count === 0 ? "All clear · monitoring" : `${count} active event${count === 1 ? "" : "s"}`}
          </p>
        </div>
      </div>
      {count === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center p-6 text-center text-xs text-gray-500">
          <AlertTriangle className="h-7 w-7 text-emerald-300" />
          <p className="mt-2 font-semibold text-dark">No active disruptions</p>
          <p className="mt-1 max-w-xs">
            Click any node on the Gantt to trigger a disruption event and watch the Cascade Protocol propose recovery plans.
          </p>
        </div>
      ) : (
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {items.map((d) => (
            <DisruptionCard key={d.id} item={d} onMitigated={onMitigated} />
          ))}
        </div>
      )}
    </div>
  );
}

function DisruptionCard({
  item,
  onMitigated,
}: {
  item: DisruptionQueueItem;
  onMitigated?: (superTripId: string, disruptionId: string, planId: string) => void;
}) {
  const meta = KIND_META[item.kind] ?? KIND_META.other;
  const Icon = meta.Icon;
  const [applyingPlanId, setApplyingPlanId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applied, setApplied] = useState<string | null>(null);

  const applyPlan = async (planId: string) => {
    setApplyingPlanId(planId);
    setError(null);
    try {
      await disruptionsApi.applyRecovery(item.super_trip_id, item.id, planId);
      setApplied(planId);
      onMitigated?.(item.super_trip_id, item.id, planId);
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
      else if (e instanceof Error) setError(e.message);
      else setError("Failed to apply plan");
    } finally {
      setApplyingPlanId(null);
    }
  };

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider", meta.tone)}>
            <Icon className="h-3 w-3" />
            {meta.label}
            {item.delta_mins !== 0 && (
              <span className="ml-1">+{item.delta_mins}m</span>
            )}
          </div>
          <h4 className="mt-1.5 truncate text-sm font-semibold text-dark" title={item.trip_title}>
            {item.trip_title}
          </h4>
          <p className="text-[11px] text-gray-500">
            Node <span className="font-mono">{item.node_id}</span> · source {item.source}
          </p>
          {item.note && (
            <p className="mt-1 rounded-lg bg-gray-50 p-2 text-[11px] text-gray-600">{item.note}</p>
          )}
        </div>
      </div>

      <div className="mt-3">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
          Recovery options
        </div>
        <div className="mt-1.5 space-y-2">
          {item.plans.map((plan) => (
            <PlanCard
              key={plan.plan_id}
              plan={plan}
              applying={applyingPlanId === plan.plan_id}
              applied={applied === plan.plan_id}
              disabled={applyingPlanId !== null || applied !== null}
              onApply={() => applyPlan(plan.plan_id)}
            />
          ))}
        </div>
      </div>

      {error && <div className="mt-2 rounded-lg bg-red-50 p-2 text-xs text-red-700">{error}</div>}
    </div>
  );
}

function PlanCard({
  plan,
  applying,
  applied,
  disabled,
  onApply,
}: {
  plan: RecoveryPlan;
  applying: boolean;
  applied: boolean;
  disabled: boolean;
  onApply: () => void;
}) {
  const kept = plan.nodes_kept;
  const cancelled = plan.nodes_cancelled;
  const shiftedOnly = plan.nodes_modified - cancelled;

  return (
    <div
      className={cn(
        "rounded-xl border p-2.5 transition-colors",
        applied ? "border-emerald-200 bg-emerald-50" : "border-gray-100 bg-white hover:border-primary/40",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold text-dark">{plan.label}</div>
          <p className="mt-0.5 text-[11px] text-gray-500">{plan.summary}</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5 text-[10px]">
            {plan.cost_delta_usd !== 0 && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-red-50 px-1.5 py-0.5 text-red-700">
                <DollarSign className="h-2.5 w-2.5" />+${plan.cost_delta_usd.toFixed(0)}
              </span>
            )}
            {plan.time_delta_mins > 0 && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-50 px-1.5 py-0.5 text-amber-700">
                <Clock className="h-2.5 w-2.5" />+{plan.time_delta_mins}m
              </span>
            )}
            {shiftedOnly > 0 && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-sky-50 px-1.5 py-0.5 text-sky-700">
                <Zap className="h-2.5 w-2.5" />{shiftedOnly} shifted
              </span>
            )}
            {cancelled > 0 && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-red-50 px-1.5 py-0.5 text-red-700">
                <Scissors className="h-2.5 w-2.5" />{cancelled} cancelled
              </span>
            )}
            <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-50 px-1.5 py-0.5 text-emerald-700">
              <CheckCircle2 className="h-2.5 w-2.5" />{kept} kept
            </span>
          </div>
        </div>
        <button
          onClick={onApply}
          disabled={disabled}
          className={cn(
            "shrink-0 rounded-full px-3 py-1.5 text-[11px] font-semibold transition-colors",
            applied
              ? "bg-emerald-600 text-white"
              : disabled && !applying
                ? "bg-gray-200 text-gray-400"
                : "bg-primary text-white hover:bg-primary/90",
          )}
        >
          {applying ? (
            <span className="flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" /> Applying
            </span>
          ) : applied ? (
            "Applied"
          ) : (
            "Apply"
          )}
        </button>
      </div>
    </div>
  );
}
