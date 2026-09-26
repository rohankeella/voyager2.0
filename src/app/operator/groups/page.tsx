"use client";

import { useEffect, useState } from "react";
import { loadBookings, seedGroups, seedCoordinators } from "@/lib/operator-data";
import type { Booking } from "@/types/operator";
import StatusBadge from "@/components/operator/status-badge";

export default function OperatorGroupsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);

  useEffect(() => {
    setBookings(loadBookings());
  }, []);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-bold text-dark">Tour Groups</h1>
      <p className="mt-1 text-sm text-gray-500">Bookings batched together for shared coordination and logistics.</p>

      <div className="mt-6 space-y-4">
        {seedGroups.map((group) => {
          const coordinator = seedCoordinators.find((c) => c.id === group.coordinatorId);
          const groupBookings = bookings.filter((b) => group.bookingIds.includes(b.id));
          const totalTravelers = groupBookings.reduce((sum, b) => sum + b.travelers, 0);

          return (
            <div key={group.id} className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
              <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                <div>
                  <h2 className="font-bold text-dark">{group.name}</h2>
                  <p className="text-sm text-gray-500">
                    {group.destination} · {group.startDate} – {group.endDate}
                  </p>
                </div>
                <StatusBadge status={group.status} />
              </div>

              <div className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm text-gray-600">
                <span>
                  <span className="font-semibold text-dark">{groupBookings.length}</span> bookings
                </span>
                <span>
                  <span className="font-semibold text-dark">{totalTravelers}</span> travelers
                </span>
                <span>
                  Coordinator: <span className="font-semibold text-dark">{coordinator?.name ?? "Unassigned"}</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
