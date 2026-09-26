"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlusCircle } from "lucide-react";
import TripCard from "@/components/dashboard/trip-card";
import { loadTrips } from "@/lib/trip-storage";
import type { Trip, TripStatus } from "@/types/trip";
import { cn } from "@/lib/utils";

const tabs: { label: string; value: TripStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Draft", value: "draft" },
  { label: "Upcoming", value: "upcoming" },
  { label: "Completed", value: "completed" },
];

export default function MyTripsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [tab, setTab] = useState<TripStatus | "all">("all");

  useEffect(() => {
    setTrips(loadTrips());
  }, []);

  const filtered = tab === "all" ? trips : trips.filter((t) => (t.status ?? "draft") === tab);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-dark">My Trips</h1>
          <p className="mt-1 text-sm text-gray-500">Every trip you&rsquo;ve planned, booked, or completed.</p>
        </div>
        <Link
          href="/onboarding"
          className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
        >
          <PlusCircle className="h-4 w-4" /> Create New Trip
        </Link>
      </div>

      <div className="mt-6 flex gap-2 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={cn(
              "shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition-colors",
              tab === t.value ? "bg-primary text-white" : "bg-white text-gray-600 hover:bg-gray-50"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="mt-10 rounded-3xl border border-dashed border-gray-200 bg-white p-10 text-center text-sm text-gray-500">
          No trips in this category yet.
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((trip, i) => (
            <TripCard key={trip.id} trip={trip} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
