"use client";

import type { StatusLight } from "@/lib/api";
import { cn } from "@/lib/utils";
import { CheckCircle2, AlertTriangle, XCircle, Circle } from "lucide-react";

type Props = {
  summary: Record<StatusLight, number>;
  activeTripCount: number;
};

const CARDS: {
  key: StatusLight;
  label: string;
  desc: string;
  Icon: React.ComponentType<{ className?: string }>;
  tone: string;
}[] = [
  { key: "green", label: "On schedule", desc: "Nodes running nominal", Icon: CheckCircle2, tone: "text-emerald-600 bg-emerald-50 border-emerald-100" },
  { key: "yellow", label: "Warning", desc: "Buffer under 30 min", Icon: AlertTriangle, tone: "text-amber-600 bg-amber-50 border-amber-100" },
  { key: "red", label: "Critical", desc: "Downstream conflict", Icon: XCircle, tone: "text-red-600 bg-red-50 border-red-100" },
  { key: "grey", label: "Complete", desc: "Past nodes / done", Icon: Circle, tone: "text-slate-500 bg-slate-50 border-slate-100" },
];

export default function LightsSummary({ summary, activeTripCount }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div className="rounded-2xl border border-primary/10 bg-primary/5 p-3">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-primary/70">
          Active trips
        </div>
        <div className="mt-1 text-2xl font-bold text-dark">{activeTripCount}</div>
        <div className="text-[10px] text-gray-500">Pending review + approved + in progress</div>
      </div>
      {CARDS.slice(0, 3).map((c) => {
        const count = summary[c.key] ?? 0;
        return (
          <div key={c.key} className={cn("rounded-2xl border p-3", c.tone)}>
            <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider opacity-80">
              <c.Icon className="h-3.5 w-3.5" />
              {c.label}
            </div>
            <div className="mt-1 text-2xl font-bold">{count}</div>
            <div className="text-[10px] opacity-70">{c.desc}</div>
          </div>
        );
      })}
    </div>
  );
}
