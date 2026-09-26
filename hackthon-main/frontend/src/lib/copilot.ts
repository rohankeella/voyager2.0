import type { SuperTrip, TripNode } from "./api";

export function tripDestination(trip: SuperTrip): string {
  const outbound = trip.nodes.find(node => node.type.startsWith("amadeus_flight"));
  return trip.global_constraints.destination || String(outbound?.execution_data.destination_city || outbound?.execution_data.destination_iata || "Your trip");
}

export function tripDays(trip: SuperTrip): number {
  const { start_date, end_date } = trip.global_constraints;
  return Math.max(1, Math.round((Date.parse(end_date.slice(0, 10)) - Date.parse(start_date.slice(0, 10))) / 86400000) + 1);
}

export function tripDayGroups(trip: SuperTrip): [string, TripNode[]][] {
  const groups = new Map<string, TripNode[]>();
  for (const node of [...trip.nodes].sort((a, b) => (a.execution_data.start_time || "").localeCompare(b.execution_data.start_time || ""))) {
    const date = node.execution_data.start_time?.slice(0, 10) || trip.global_constraints.start_date.slice(0, 10);
    groups.set(date, [...(groups.get(date) || []), node]);
  }
  return [...groups];
}
