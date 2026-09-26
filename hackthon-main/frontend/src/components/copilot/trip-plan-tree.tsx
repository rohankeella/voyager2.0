"use client";

import { CalendarDays, MapPin, Plane, Hotel, Utensils, Car, Compass } from "lucide-react";
import { useEffect, useRef } from "react";
import type { SuperTrip } from "@/lib/api";
import { tripDayGroups, tripDestination, tripDays } from "@/lib/copilot";

export default function TripPlanTree({ trip, selectedId, onSelect, busy }: {
  trip: SuperTrip | null; selectedId: string | null; onSelect: (id: string) => void; busy: boolean;
}) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const selected = root.current?.querySelector<HTMLElement>('[aria-current="true"]');
    if (selected) {
      selected.closest("details")?.setAttribute("open", "");
      selected.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [selectedId]);
  if (!trip) return <div className="p-6 text-slate-600"><Compass className="mb-5 h-7 w-7 text-primary" /><h2 className="text-lg font-semibold text-dark">Your journey starts here</h2><p className="mt-3 text-sm leading-relaxed">{busy ? "Building your itinerary and checking its schedule…" : "Tell the co-pilot where you want to go. Your flights, stays, meals, and activities will appear here, organized by day."}</p></div>;
  return <div ref={root} className="min-h-0 flex-1 overflow-y-auto" aria-label="Day-by-day itinerary" aria-busy={busy}>
    <div className="border-b border-slate-200 p-4">
      <h2 className="text-xl font-semibold text-dark">{tripDestination(trip)}</h2>
      <p className="mt-1 text-sm text-slate-600">{tripDays(trip)} days · {trip.nodes.length} stops</p>
      <p className="mt-3 text-xs leading-relaxed text-slate-600">Draft estimates only. Nothing is booked. Times shown in UTC; city markers are approximate.</p>
    </div>
    {tripDayGroups(trip).map(([date, nodes]) => <details key={date} open className="border-b border-slate-200">
      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-dark hover:bg-slate-50">
        <CalendarDays className="mr-2 inline h-4 w-4 text-primary" />
        {new Date(`${date}T12:00:00Z`).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" })}
        <span className="ml-2 font-normal text-slate-600">{nodes.length} stops</span>
      </summary>
      <ol className="space-y-1 px-2 pb-3">
        {nodes.map(node => {
          const Icon = node.type.includes("flight") ? Plane : node.type.includes("hotel") ? Hotel : node.type === "meal" ? Utensils : node.type === "otp_ground_transfer" ? Car : MapPin;
          return <li key={node.node_id}><button type="button" aria-current={selectedId === node.node_id} onClick={() => onSelect(node.node_id)} className={`flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left focus-visible:outline-2 focus-visible:outline-primary ${selectedId === node.node_id ? "bg-teal-50 text-teal-900" : "text-slate-700 hover:bg-slate-50"}`}>
            <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <span className="min-w-0 flex-1"><span className="block text-sm font-medium">{node.title || node.type.replaceAll("_", " ")}</span><span className="mt-1 block text-xs text-slate-600">{node.execution_data.start_time?.slice(11, 16) || "Time flexible"} · ${node.financials.cost_usd.toFixed(0)} estimate</span></span>
          </button></li>;
        })}
      </ol>
    </details>)}
  </div>;
}
