"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { loadChangeRequests, updateChangeRequestStatus, loadBookings } from "@/lib/operator-data";
import type { ChangeRequestStatus, ItineraryChangeRequest } from "@/types/operator";
import type { Booking } from "@/types/operator";
import StatusBadge from "@/components/operator/status-badge";

const statuses: ChangeRequestStatus[] = ["open", "reviewing", "resolved", "rejected"];

export default function OperatorChangesPage() {
  const [requests, setRequests] = useState<ItineraryChangeRequest[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);

  useEffect(() => {
    setRequests(loadChangeRequests());
    setBookings(loadBookings());
  }, []);

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-6 w-6 text-amber-500" />
        <h1 className="text-2xl font-bold text-dark">Itinerary Changes</h1>
      </div>
      <p className="mt-1 text-sm text-gray-500">
        Disruptions and modification requests, with the impact and a suggested fix already worked out.
      </p>

      <div className="mt-6 space-y-4">
        {requests.map((r) => {
          const booking = bookings.find((b) => b.id === r.bookingId);
          return (
            <div key={r.id} className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
              <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                    {r.raisedBy === "system" ? "Auto-detected" : `Raised by ${r.raisedBy}`} ·{" "}
                    {booking ? booking.customerName : r.bookingId}
                  </p>
                  <h2 className="mt-1 font-bold text-dark">{r.reason}</h2>
                </div>
                <StatusBadge status={r.status} />
              </div>

              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-gray-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Impact</p>
                  <p className="mt-1 text-sm text-gray-700">{r.impact}</p>
                </div>
                <div className="rounded-2xl bg-primary/5 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-primary">Suggested Resolution</p>
                  <p className="mt-1 text-sm text-gray-700">{r.suggestedResolution}</p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                {booking && (
                  <Link href={`/operator/bookings/${booking.id}`} className="text-xs font-semibold text-primary hover:underline">
                    View booking →
                  </Link>
                )}
                <div className="ml-auto flex gap-2">
                  {statuses.map((s) => (
                    <button
                      key={s}
                      onClick={() => setRequests(updateChangeRequestStatus(r.id, s))}
                      className={`rounded-full border px-3 py-1.5 text-xs font-semibold capitalize transition-colors ${
                        r.status === s
                          ? "border-dark bg-dark text-white"
                          : "border-gray-200 text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
        {requests.length === 0 && (
          <p className="rounded-3xl border border-dashed border-gray-200 bg-white p-10 text-center text-sm text-gray-400">
            No open itinerary changes.
          </p>
        )}
      </div>
    </div>
  );
}
