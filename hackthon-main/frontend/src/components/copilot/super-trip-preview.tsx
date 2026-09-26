"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, Loader2, AlertTriangle, CreditCard, Route } from "lucide-react";
import { superTripsApi, type SuperTrip, type SuperTripDetail, type SuperTripPayment, type TripNode, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import TripNodeCard from "./trip-node-card";
import CheckoutDialog from "./checkout-dialog";

type Props = {
  trip: SuperTrip;
  persistedId: string | null;
  hitlRequired: boolean;
  hitlReason: string | null;
  warnings: string[];
  onApproved?: (record: SuperTripDetail) => void;
  onFocusNode?: (nodeId: string) => void;
  focusNodeId?: string | null;
};

const DAY_MS = 24 * 3600 * 1000;

function fmtRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return start;
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${s.toLocaleDateString(undefined, opts)} – ${e.toLocaleDateString(undefined, { ...opts, year: "numeric" })}`;
}

/** Group nodes under "Day N" headings, keeping the planner's order inside each day. */
function groupByDay(nodes: TripNode[], tripStart: string) {
  const start = new Date(tripStart);
  start.setHours(0, 0, 0, 0);
  const groups: { key: string; label: string; items: { node: TripNode }[] }[] = [];
  nodes.forEach((node) => {
    const t = node.execution_data.start_time ? new Date(node.execution_data.start_time) : null;
    let key = "unscheduled";
    let label = "Unscheduled";
    if (t && !Number.isNaN(t.getTime())) {
      const day = new Date(t);
      day.setHours(0, 0, 0, 0);
      const n = Math.max(1, Math.round((day.getTime() - start.getTime()) / DAY_MS) + 1);
      key = `d${n}`;
      label = `Day ${n} · ${t.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}`;
    }
    const group = groups.find((g) => g.key === key) ?? groups[groups.push({ key, label, items: [] }) - 1];
    group.items.push({ node });
  });
  return groups;
}

export default function SuperTripPreview({
  trip,
  persistedId,
  hitlRequired,
  hitlReason,
  warnings,
  onApproved,
  onFocusNode,
  focusNodeId,
}: Props) {
  const [approvedIds, setApprovedIds] = useState<Set<string>>(new Set());
  const [approving, setApproving] = useState(false);
  const [approveError, setApproveError] = useState<string | null>(null);
  const [committed, setCommitted] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [payment, setPayment] = useState<SuperTripPayment | null>(null);

  const g = trip.global_constraints;
  const totalCost = trip.nodes.reduce((sum, n) => sum + n.financials.cost_usd, 0);
  const budget = g.max_budget_usd;
  const overBudget = totalCost > budget;
  const days =
    Math.max(1, Math.floor((new Date(g.end_date).getTime() - new Date(g.start_date).getTime()) / DAY_MS)) + 1;
  const groups = useMemo(() => groupByDay(trip.nodes, g.start_date), [trip.nodes, g.start_date]);

  const highValueCount = trip.nodes.filter((n) => n.requires_approval || n.financials.cost_usd >= 500).length;
  const allApproved = approvedIds.size >= highValueCount || highValueCount === 0;
  const pendingCount = Math.max(0, highValueCount - approvedIds.size);
  const approveDisabled = approving || !persistedId || (hitlRequired && !allApproved);

  const status = committed ? "approved" : trip.status;
  const statusClass =
    status === "approved"
      ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20"
      : status === "pending_review"
        ? "bg-amber-50 text-amber-800 ring-amber-600/25"
        : "bg-slate-100 text-slate-700 ring-slate-500/20";

  const handleApproveAll = async () => {
    if (!persistedId) {
      setApproveError(
        "This preview isn't persisted (you may not be signed in). Sign in and re-plan to save it.",
      );
      return;
    }
    setApproving(true);
    setApproveError(null);
    try {
      const record = await superTripsApi.approve(persistedId);
      setCommitted(true);
      onApproved?.(record);
    } catch (e) {
      if (e instanceof ApiError) {
        setApproveError(e.message);
      } else if (e instanceof Error) {
        setApproveError(e.message);
      } else {
        setApproveError("Approval failed. Try again.");
      }
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white">
      {/* header */}
      <div className="shrink-0 border-b border-slate-100 px-4 pb-4 pt-3.5">
        <div className="flex items-start justify-between gap-3">
          <h2 className="min-w-0 text-lg font-semibold leading-snug text-slate-900 [text-wrap:balance]">
            {g.destination || "Trip"} — {days} days
          </h2>
          <span
            className={cn(
              "mt-0.5 inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset",
              statusClass,
            )}
          >
            {committed && <CheckCircle2 className="h-3 w-3" />}
            {status.replace("_", " ")}
          </span>
        </div>
        <p className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-slate-500">
          <span className="tabular-nums">{fmtRange(g.start_date, g.end_date)}</span>
          <span aria-hidden>·</span>
          <span>{trip.nodes.length} stop{trip.nodes.length === 1 ? "" : "s"}</span>
          <span aria-hidden>·</span>
          <span className="font-mono text-[11px]">{trip.super_trip_id}</span>
          {persistedId && (
            <span className="inline-flex items-center gap-0.5 text-emerald-700">
              <CheckCircle2 className="h-3 w-3" /> saved
            </span>
          )}
        </p>

        <div className="mt-3.5">
          <div className="flex items-baseline justify-between text-xs">
            <span className="text-slate-500">Estimated total</span>
            <span className="tabular-nums">
              <span className={cn("text-sm font-semibold", overBudget ? "text-red-700" : "text-slate-900")}>
                ${totalCost.toFixed(0)}
              </span>
              <span className="text-slate-500"> of ${budget.toFixed(0)}</span>
            </span>
          </div>
          <div
            className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100"
            role="meter"
            aria-label="Budget used"
            aria-valuemin={0}
            aria-valuemax={budget}
            aria-valuenow={Math.round(totalCost)}
          >
            <div
              className={cn("h-full rounded-full", overBudget ? "bg-red-500" : "bg-primary")}
              style={{ width: `${Math.min(100, (totalCost / Math.max(budget, 1)) * 100)}%` }}
            />
          </div>
        </div>

        {hitlRequired && !committed && pendingCount > 0 && (
          <div className="mt-3.5 flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2.5 text-xs text-amber-900">
            <AlertTriangle className="mt-px h-3.5 w-3.5 shrink-0 text-amber-700" />
            <div>
              <span className="font-semibold">
                {pendingCount} booking{pendingCount === 1 ? "" : "s"} need{pendingCount === 1 ? "s" : ""} your approval.
              </span>{" "}
              <span className="text-amber-800">
                {/* The standard reason only restates the count; show it when it says something else. */}
                {hitlReason && !/node\(s\) require your approval/.test(hitlReason)
                  ? hitlReason
                  : "Approve each one below, then save the trip."}
              </span>
            </div>
          </div>
        )}

        {warnings.length > 0 && !committed && (
          <details className="mt-2.5 text-xs text-slate-500">
            <summary className="cursor-pointer select-none rounded hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">
              {warnings.length} planning note{warnings.length === 1 ? "" : "s"}
            </summary>
            <ul className="mt-1 space-y-0.5 pl-4">
              {warnings.slice(0, 4).map((w, i) => (
                <li key={i} className="list-disc">{w}</li>
              ))}
            </ul>
          </details>
        )}
      </div>

      {/* itinerary, grouped by day */}
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {groups.map((group) => (
          <section key={group.key} aria-label={group.label}>
            <h3 className="sticky top-0 z-10 bg-white/95 px-2 pb-1.5 pt-3 text-xs font-semibold text-slate-500">
              {group.label}
            </h3>
            <ul className="space-y-0.5">
              {group.items.map(({ node }) => (
                <li key={node.node_id}>
                  <TripNodeCard
                    node={node}
                    focused={focusNodeId === node.node_id}
                    onFocus={onFocusNode}
                    approved={committed || approvedIds.has(node.node_id)}
                    onApprove={committed ? undefined : (id) => setApprovedIds((prev) => new Set(prev).add(id))}
                  />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {/* footer */}
      {!committed && (
        <div className="shrink-0 border-t border-slate-100 p-3">
          {approveError && (
            <div role="alert" className="mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">
              {approveError}
            </div>
          )}
          <button
            onClick={handleApproveAll}
            disabled={approveDisabled}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 disabled:bg-slate-200 disabled:text-slate-500"
          >
            {approving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Approving…
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" /> Approve & Save Trip
              </>
            )}
          </button>
          {!persistedId ? (
            <p className="mt-2 text-center text-xs text-slate-500">
              Sign in first — the plan needs a signed-in user to persist.
            </p>
          ) : (
            hitlRequired &&
            !allApproved && (
              <p className="mt-2 text-center text-xs text-amber-800">
                Approve the {pendingCount} pending high-value item{pendingCount === 1 ? "" : "s"} above first.
              </p>
            )
          )}
        </div>
      )}

      {/* Post-approval: checkout with Razorpay Route */}
      {committed && persistedId && (
        <div className="shrink-0 border-t border-slate-100 p-3">
          {payment && payment.status === "captured" ? (
            <div className="flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-xs text-emerald-800">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <div>
                <div className="font-semibold">Paid · funds routed to {payment.transfers.length} accounts</div>
                <div className="mt-0.5 tabular-nums text-emerald-700">
                  ${payment.total_usd.toFixed(2)} · {payment.razorpay_payment_id}
                </div>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setCheckoutOpen(true)}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600/40 focus-visible:ring-offset-2"
            >
              <CreditCard className="h-4 w-4" />
              Checkout with Razorpay Route
            </button>
          )}
        </div>
      )}

      {checkoutOpen && persistedId && (
        <CheckoutDialog
          superTripId={persistedId}
          totalHint={totalCost}
          onClose={() => setCheckoutOpen(false)}
          onCaptured={(p) => setPayment(p)}
        />
      )}
    </div>
  );
}

const PIPELINE = [
  { name: "Planner", text: "drafts the route, days and stops from your request." },
  { name: "Executor", text: "prices flights, stays and transfers for each stop." },
  { name: "Supervisor", text: "checks dates, dependencies and your budget." },
];

export function PreviewEmpty() {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-6">
      <div className="my-auto">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Route className="h-5 w-5" />
        </span>
        <h2 className="mt-4 text-base font-semibold text-slate-900">Your itinerary appears here</h2>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-500">
          Every stop is listed by day. Bookings of $500 or more wait for your approval before anything is paid.
        </p>
        <ol className="mt-6 space-y-3">
          {PIPELINE.map((step, i) => (
            <li key={step.name} className="flex gap-3 text-sm">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold tabular-nums text-slate-600">
                {i + 1}
              </span>
              <p className="pt-0.5 leading-snug text-slate-600">
                <span className="font-semibold text-slate-900">{step.name}</span> {step.text}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export function PreviewSkeleton() {
  return (
    <div
      className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white"
      aria-busy="true"
      aria-label="Planning itinerary"
    >
      <div className="border-b border-slate-100 px-4 pb-4 pt-4">
        <div className="h-5 w-2/3 animate-pulse rounded-md bg-slate-100" />
        <div className="mt-2.5 h-3 w-1/2 animate-pulse rounded-md bg-slate-100" />
        <div className="mt-5 h-1.5 w-full animate-pulse rounded-full bg-slate-100" />
      </div>
      <div className="space-y-4 px-4 pt-4">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="flex gap-3">
            <div className="h-8 w-8 shrink-0 animate-pulse rounded-lg bg-slate-100" />
            <div className="flex-1 space-y-2 pt-0.5">
              <div className="h-3 w-3/5 animate-pulse rounded bg-slate-100" />
              <div className="h-2.5 w-2/5 animate-pulse rounded bg-slate-100" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
