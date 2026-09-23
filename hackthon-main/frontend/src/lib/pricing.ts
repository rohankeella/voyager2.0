import type { Trip } from "@/types/trip";
import type { CostBreakdownItem } from "@/types/operator";
import { destinations } from "@/lib/mock-data";

// Rough per-traveler-per-day rate in INR, by budget tier. Used as the pricing
// engine for the "Price" stage of the lifecycle. A real system would price
// against live vendor rates instead of a flat table.
const budgetDailyRateINR: Record<string, number> = {
  backpacker: 1500,
  budget: 3000,
  comfortable: 5500,
  premium: 9000,
  luxury: 18000,
};

const USD_TO_INR = 83;

function diffDays(start: string, end: string): number {
  if (!start || !end) return 0;
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  if (Number.isNaN(s) || Number.isNaN(e) || e < s) return 0;
  return Math.round((e - s) / 86400000) + 1;
}

export type TripCostEstimate = {
  days: number;
  dailyRate: number;
  breakdown: CostBreakdownItem[];
  total: number;
};

export function estimateTripCost(trip: Trip): TripCostEstimate {
  const days = trip.days.length || diffDays(trip.startDate, trip.endDate) || 3;
  const travelers = Math.max(trip.travelers || 1, 1);
  const dest = destinations.find((d) => d.slug === trip.destinationSlug);
  const dailyRate =
    budgetDailyRateINR[trip.budget] ?? (dest ? Math.round(dest.estimatedDailyCost * USD_TO_INR) : 4500);

  const base = dailyRate * days * travelers;
  const accommodation = Math.round(base * 0.4);
  const activities = Math.round(base * 0.25);
  const food = Math.round(base * 0.2);
  const transport = Math.round(base * 0.15) + 3500 * travelers;
  const subtotal = accommodation + activities + food + transport;
  const serviceFee = Math.round(subtotal * 0.05);
  const total = subtotal + serviceFee;

  return {
    days,
    dailyRate,
    breakdown: [
      { label: "Accommodation", amount: accommodation },
      { label: "Activities & Experiences", amount: activities },
      { label: "Food & Dining", amount: food },
      { label: "Transport & Transfers", amount: transport },
      { label: "Service Fee", amount: serviceFee },
    ],
    total,
  };
}

export function formatINR(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")}`;
}
