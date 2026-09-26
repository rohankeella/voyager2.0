"use client";

/**
 * DTO-P3 Phase 5 — Trigger Disruption dialog.
 *
 * Modal opened by clicking a node on the LiveGantt. Lets the operator
 * (or demo runner) manually inject a disruption event so the Cascade
 * Protocol kicks off. In production this would come from a real webhook;
 * for the hackathon demo the dialog is the ingester.
 */

import { useEffect, useState } from "react";
import { X, Zap, Loader2 } from "lucide-react";
import {
  disruptionsApi,
  ApiError,
  type SuperDisruptionKind,
  type GanttNode,
  type GanttTrip,
  type SuperTripDisruption,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  trip: GanttTrip;
  node: GanttNode;
  onClose: () => void;
  onCreated: (d: SuperTripDisruption) => void;
};

const KIND_OPTIONS: { value: SuperDisruptionKind; label: string; hint: string }[] = [
  { value: "delay", label: "Delay", hint: "Flight/transfer runs late by N minutes" },
  { value: "cancellation", label: "Cancellation", hint: "Node cancelled outright" },
  { value: "weather", label: "Weather", hint: "Weather-driven closure at destination" },
  { value: "overbooked", label: "Overbooked", hint: "Vendor could not honour reservation" },
  { value: "capacity", label: "Capacity", hint: "Attraction hit visitor cap" },
];

const DELAY_PRESETS = [30, 60, 120, 180, 300];

export default function TriggerDisruptionDialog({ trip, node, onClose, onCreated }: Props) {
  const [kind, setKind] = useState<SuperDisruptionKind>("delay");
  const [deltaMins, setDeltaMins] = useState<number>(180);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Close on Esc
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, busy]);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const d = await disruptionsApi.trigger(trip.super_trip_id, {
        node_id: node.node_id,
        kind,
        delta_mins: kind === "delay" ? deltaMins : 0,
        note: note.trim() || undefined,
        source: "operator_manual",
      });
      onCreated(d);
      onClose();
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
      else if (e instanceof Error) setError(e.message);
      else setError("Failed to trigger disruption");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md overflow-hidden rounded-3xl bg-white shadow-2xl"
      >
        <div className="flex items-start justify-between gap-2 border-b border-gray-100 p-5">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-red-600">
              <Zap className="h-3 w-3" /> Trigger disruption
            </div>
            <h2 className="mt-1 text-base font-bold text-dark">{node.title}</h2>
            <p className="mt-0.5 text-[11px] text-gray-500">
              <span className="font-mono">{trip.super_trip_id}</span> · {node.node_id} · ${node.cost_usd.toFixed(0)}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={busy}
            className="flex h-8 w-8 items-center justify-center rounded-full text-gray-400 hover:bg-gray-100 hover:text-dark disabled:opacity-40"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          {/* kind */}
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">Event type</label>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {KIND_OPTIONS.map((k) => (
                <button
                  key={k.value}
                  onClick={() => setKind(k.value)}
                  disabled={busy}
                  className={cn(
                    "rounded-xl border p-2.5 text-left text-xs transition-colors",
                    kind === k.value
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-gray-200 text-gray-600 hover:border-primary/50",
                  )}
                >
                  <div className="font-semibold">{k.label}</div>
                  <div className="mt-0.5 text-[10px] opacity-70">{k.hint}</div>
                </button>
              ))}
            </div>
          </div>

          {/* delta_mins — only for delay */}
          {kind === "delay" && (
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">
                Delay in minutes
              </label>
              <div className="mt-2 flex gap-2">
                <input
                  type="number"
                  min={-720}
                  max={1440}
                  step={15}
                  value={deltaMins}
                  onChange={(e) => setDeltaMins(Number(e.target.value))}
                  disabled={busy}
                  className="flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-dark focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
                <div className="flex flex-wrap gap-1">
                  {DELAY_PRESETS.map((m) => (
                    <button
                      key={m}
                      onClick={() => setDeltaMins(m)}
                      disabled={busy}
                      className={cn(
                        "rounded-full px-2.5 py-1 text-[11px] font-medium",
                        deltaMins === m
                          ? "bg-primary text-white"
                          : "border border-gray-200 text-gray-500 hover:border-primary hover:text-primary",
                      )}
                    >
                      {m}m
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* note */}
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">
              Note <span className="normal-case text-gray-400">(optional)</span>
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={busy}
              rows={2}
              placeholder="e.g. Weather advisory issued; expected 3h delay."
              className="mt-2 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-dark focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          {error && (
            <div className="rounded-lg bg-red-50 p-2 text-xs text-red-700">{error}</div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-gray-100 bg-gray-50 p-4">
          <button
            onClick={onClose}
            disabled={busy}
            className="rounded-full px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-white disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy}
            className="flex items-center gap-1 rounded-full bg-red-600 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-red-700 disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            Trigger cascade
          </button>
        </div>
      </div>
    </div>
  );
}
