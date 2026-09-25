"use client";

/**
 * DTO-P3 Phase 4 — Vendor Status Hub.
 *
 * Per PRD § "Vendor and Participant Coordination Matrix":
 *   Aggregated visibility on third-party API confirmations. Each row groups
 *   nodes by vendor_account and shows how much has been routed vs still
 *   pending, so operators can spot un-settled inventory before travelers
 *   check in.
 */

import type { VendorMatrixRow } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Building2, CheckCircle2, AlertCircle } from "lucide-react";

type Props = {
  rows: VendorMatrixRow[];
};

export default function VendorMatrix({ rows }: Props) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 p-4">
        <div>
          <h3 className="text-sm font-bold text-dark">Vendor Status Hub</h3>
          <p className="text-[11px] text-gray-500">
            Payment routing across {rows.length} vendor account{rows.length === 1 ? "" : "s"}
          </p>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center p-6 text-center">
          <Building2 className="h-8 w-8 text-gray-300" />
          <p className="mt-2 text-sm font-semibold text-dark">No vendor activity yet</p>
          <p className="mt-1 max-w-xs text-xs text-gray-500">
            As DAG nodes get booked and paid, vendor totals will roll up here.
          </p>
        </div>
      ) : (
        <div className="flex-1 space-y-2 overflow-y-auto p-4">
          {rows.map((row) => (
            <VendorRow key={row.vendor_account} row={row} />
          ))}
        </div>
      )}
    </div>
  );
}

function VendorRow({ row }: { row: VendorMatrixRow }) {
  const pending = row.payment_status["unpaid"] ?? 0;
  const escrowed = row.payment_status["escrowed"] ?? 0;
  const routed = row.payment_status["routed"] ?? 0;
  const refunded = row.payment_status["refunded"] ?? 0;
  const ratio = Math.max(0, Math.min(1, row.settled_ratio));

  const typeSummary = Object.entries(row.types)
    .map(([t, c]) => `${c}× ${t.replace("amadeus_", "").replace("otp_", "").replace("_", " ")}`)
    .join(" · ");

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Building2 className="h-3.5 w-3.5 text-slate-500" />
            <span className="truncate font-mono text-xs font-semibold text-dark">
              {row.vendor_account}
            </span>
          </div>
          <p className="mt-0.5 text-[11px] text-gray-500">{typeSummary || "—"}</p>
        </div>
        <div className="text-right">
          <div className="text-sm font-bold text-dark">${row.total_usd.toFixed(0)}</div>
          <div className="text-[10px] text-gray-400">{row.node_count} node{row.node_count === 1 ? "" : "s"}</div>
        </div>
      </div>

      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full bg-emerald-500"
          style={{ width: `${ratio * 100}%` }}
        />
      </div>

      <div className="mt-2 flex flex-wrap gap-1 text-[10px]">
        <StatusPill count={routed} label="routed" tone="emerald" icon={<CheckCircle2 className="h-3 w-3" />} />
        {escrowed > 0 && <StatusPill count={escrowed} label="escrowed" tone="sky" />}
        <StatusPill count={pending} label="pending" tone="amber" icon={<AlertCircle className="h-3 w-3" />} />
        {refunded > 0 && <StatusPill count={refunded} label="refunded" tone="rose" />}
      </div>
    </div>
  );
}

function StatusPill({
  count,
  label,
  tone,
  icon,
}: {
  count: number;
  label: string;
  tone: "emerald" | "amber" | "sky" | "rose";
  icon?: React.ReactNode;
}) {
  if (count === 0) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-medium",
        tone === "emerald" && "bg-emerald-50 text-emerald-700",
        tone === "amber" && "bg-amber-50 text-amber-700",
        tone === "sky" && "bg-sky-50 text-sky-700",
        tone === "rose" && "bg-rose-50 text-rose-700",
      )}
    >
      {icon}
      {count} {label}
    </span>
  );
}
