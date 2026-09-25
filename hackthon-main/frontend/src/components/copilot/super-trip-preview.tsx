"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, DollarSign, Calendar, MapPin, AlertTriangle, CreditCard } from "lucide-react";
import { superTripsApi, type SuperTrip, type SuperTripDetail, type SuperTripPayment, ApiError } from "@/lib/api";
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

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
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

  const totalCost = trip.nodes.reduce((sum, n) => sum + n.financials.cost_usd, 0);
  const budget = trip.global_constraints.max_budget_usd;
  const overBudget = totalCost > budget;
  const days =
    Math.max(
      1,
      Math.round(
        (new Date(trip.global_constraints.end_date).getTime() -
          new Date(trip.global_constraints.start_date).getTime()) /
          (24 * 3600 * 1000),
      ),
    ) + 1;

  const highValueCount = trip.nodes.filter((n) => n.requires_approval || n.financials.cost_usd >= 500).length;
  const allApproved = approvedIds.size >= highValueCount || highValueCount === 0;

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
    <div className="flex h-full flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
      {/* header */}
      <div className="border-b border-gray-100 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-primary">
              SuperTrip · {trip.super_trip_id}
            </div>
            <h2 className="mt-1 text-lg font-bold text-dark">
              {trip.global_constraints.home_location || "Trip"} — {days} days
            </h2>
            <p className="mt-0.5 text-xs text-gray-500">
              Status:{" "}
              <span className={cn("font-medium", committed ? "text-emerald-600" : "text-amber-600")}>
                {committed ? "approved" : trip.status.replace("_", " ")}
              </span>
              {persistedId && (
                <>
                  {" "}
                  · <span className="font-mono">saved</span>
                </>
              )}
            </p>
          </div>
          {committed && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700">
              <CheckCircle2 className="h-3 w-3" /> Approved
            </span>
          )}
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
          <div className="rounded-xl bg-gray-50 p-2.5">
            <div className="flex items-center gap-1 text-gray-500">
              <DollarSign className="h-3 w-3" /> Total
            </div>
            <div className={cn("mt-0.5 text-sm font-bold", overBudget ? "text-red-600" : "text-dark")}>
              ${totalCost.toFixed(0)}
              <span className="ml-1 text-[10px] font-normal text-gray-400">/ ${budget.toFixed(0)}</span>
            </div>
          </div>
          <div className="rounded-xl bg-gray-50 p-2.5">
            <div className="flex items-center gap-1 text-gray-500">
              <MapPin className="h-3 w-3" /> Nodes
            </div>
            <div className="mt-0.5 text-sm font-bold text-dark">{trip.nodes.length}</div>
          </div>
          <div className="rounded-xl bg-gray-50 p-2.5">
            <div className="flex items-center gap-1 text-gray-500">
              <Calendar className="h-3 w-3" /> Dates
            </div>
            <div className="mt-0.5 truncate text-xs font-semibold text-dark">
              {fmtDate(trip.global_constraints.start_date)}
            </div>
          </div>
        </div>

        {hitlRequired && !committed && (
          <div className="mt-4 flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div className="flex-1">
              <div className="font-semibold">Review & Approve required</div>
              <div className="mt-0.5 text-amber-700">{hitlReason || "High-value bookings need your OK before payment is routed."}</div>
            </div>
          </div>
        )}

        {warnings.length > 0 && !committed && (
          <details className="mt-3 text-xs text-gray-500">
            <summary className="cursor-pointer">{warnings.length} planning notes</summary>
            <ul className="mt-1 space-y-0.5 pl-4">
              {warnings.slice(0, 4).map((w, i) => (
                <li key={i} className="list-disc">{w}</li>
              ))}
            </ul>
          </details>
        )}
      </div>

      {/* node list */}
      <div className="flex-1 space-y-2.5 overflow-y-auto p-5">
        {trip.nodes.map((n, i) => (
          <div
            key={n.node_id}
            role={onFocusNode ? "button" : undefined}
            tabIndex={onFocusNode ? 0 : undefined}
            onClick={() => onFocusNode?.(n.node_id)}
            onKeyDown={(e) => {
              if (onFocusNode && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                onFocusNode(n.node_id);
              }
            }}
            className={cn(
              "cursor-pointer rounded-2xl outline-none transition-shadow",
              onFocusNode && "hover:ring-2 hover:ring-primary/30 focus:ring-2 focus:ring-primary/40",
              focusNodeId === n.node_id && "ring-2 ring-primary/60",
            )}
          >
            <TripNodeCard
              node={n}
              index={i}
              approved={committed || approvedIds.has(n.node_id)}
              onApprove={
                committed
                  ? undefined
                  : (id) => setApprovedIds((prev) => new Set(prev).add(id))
              }
            />
          </div>
        ))}
      </div>

      {/* footer */}
      {!committed && (
        <div className="border-t border-gray-100 p-4">
          {approveError && (
            <div className="mb-2 rounded-lg bg-red-50 p-2 text-xs text-red-700">{approveError}</div>
          )}
          <button
            onClick={handleApproveAll}
            disabled={approving || !persistedId || (hitlRequired && !allApproved)}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded-full py-2.5 text-sm font-semibold text-white transition-colors",
              approving || !persistedId || (hitlRequired && !allApproved)
                ? "bg-gray-300"
                : "bg-primary hover:bg-primary/90",
            )}
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
          {!persistedId && (
            <p className="mt-2 text-center text-[11px] text-gray-400">
              Sign in first — the plan needs a signed-in user to persist.
            </p>
          )}
          {hitlRequired && !allApproved && (
            <p className="mt-2 text-center text-[11px] text-amber-600">
              Approve the {highValueCount - approvedIds.size} pending high-value item(s) above first.
            </p>
          )}
        </div>
      )}

      {/* Post-approval: checkout with Razorpay Route */}
      {committed && persistedId && (
        <div className="border-t border-gray-100 p-4">
          {payment && payment.status === "captured" ? (
            <div className="flex items-center justify-between gap-2 rounded-xl bg-emerald-50 p-3 text-xs">
              <div className="flex items-center gap-2 text-emerald-800">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <div>
                  <div className="font-semibold">Paid · funds routed to {payment.transfers.length} accounts</div>
                  <div className="mt-0.5 text-[10px] text-emerald-700">
                    ${payment.total_usd.toFixed(2)} · {payment.razorpay_payment_id}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setCheckoutOpen(true)}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-emerald-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700"
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
