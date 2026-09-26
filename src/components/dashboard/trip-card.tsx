"use client";

import Image from "next/image";
import Link from "next/link";
import { Calendar, Users, Wallet, Check } from "lucide-react";
import type { Trip } from "@/types/trip";
import { tripStatusBadgeStyles, tripStatusLabels, tripStatusSteps } from "@/types/trip";
import { cn } from "@/lib/utils";

const budgetLabels: Record<string, string> = {
  backpacker: "₹15,000",
  budget: "₹42,000",
  comfortable: "₹65,000",
  premium: "₹1,10,000",
  luxury: "₹2,50,000+",
};

function formatRange(start: string, end: string) {
  if (!start || !end) return "Dates not set";
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  try {
    return `${new Date(start).toLocaleDateString("en-US", opts)} – ${new Date(end).toLocaleDateString("en-US", opts)}`;
  } catch {
    return `${start} – ${end}`;
  }
}

function ctaFor(status: Trip["status"]) {
  switch (status) {
    case "completed":
      return "View Memories";
    case "draft":
      return "Continue Planning";
    default:
      return "View Details";
  }
}

export default function TripCard({ trip, index = 0 }: { trip: Trip; index?: number }) {
  const status = trip.status ?? "draft";
  const activeStepIndex = tripStatusSteps.indexOf(status as (typeof tripStatusSteps)[number]);

  return (
    <div
      className="animate-fade-in-up overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm transition-shadow hover:shadow-md"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="relative h-36 w-full bg-gray-100">
        {trip.coverImage ? (
          <Image src={trip.coverImage} alt={trip.destination} fill sizes="400px" className="object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary/20 to-secondary/20 text-sm font-medium text-primary">
            {trip.destination || "New trip"}
          </div>
        )}
        <span
          className={cn(
            "absolute left-3 top-3 rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize backdrop-blur-sm",
            tripStatusBadgeStyles[status]
          )}
        >
          {tripStatusLabels[status]}
        </span>
      </div>

      <div className="p-5">
        <h3 className="text-base font-bold text-dark">{trip.name || trip.destination || "Untitled trip"}</h3>

        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" /> {formatRange(trip.startDate, trip.endDate)}
          </span>
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" /> {trip.travelers} Traveler{trip.travelers === 1 ? "" : "s"}
          </span>
          <span className="flex items-center gap-1">
            <Wallet className="h-3.5 w-3.5" /> {budgetLabels[trip.budget] ?? trip.budget ?? "Budget TBD"}
          </span>
        </div>

        {status !== "draft" && (
          <div className="mt-5 flex items-center">
            {tripStatusSteps.map((step, i) => {
              const done = i <= activeStepIndex;
              const isLast = i === tripStatusSteps.length - 1;
              return (
                <div key={step} className={cn("flex items-center", !isLast && "flex-1")}>
                  <div className="flex flex-col items-center gap-1">
                    <span
                      className={cn(
                        "flex h-5 w-5 items-center justify-center rounded-full border-2 text-[10px]",
                        done ? "border-primary bg-primary text-white" : "border-gray-200 bg-white text-gray-300"
                      )}
                    >
                      {done ? <Check className="h-3 w-3" /> : ""}
                    </span>
                    <span className={cn("text-[10px] font-medium capitalize", done ? "text-primary" : "text-gray-400")}>
                      {tripStatusLabels[step]}
                    </span>
                  </div>
                  {!isLast && (
                    <span className={cn("mx-1 h-0.5 flex-1", i < activeStepIndex ? "bg-primary" : "bg-gray-200")} />
                  )}
                </div>
              );
            })}
          </div>
        )}

        <Link
          href={`/planner?tripId=${trip.id}`}
          className="mt-5 flex w-full items-center justify-center gap-1 rounded-full border border-gray-200 py-2.5 text-sm font-semibold text-dark transition-colors hover:border-primary hover:text-primary"
        >
          {ctaFor(status)} →
        </Link>
      </div>
    </div>
  );
}
