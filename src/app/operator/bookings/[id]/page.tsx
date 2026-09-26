"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MapPin, Calendar, Users, Mail } from "lucide-react";
import {
  loadBookings,
  updateBooking,
  loadChangeRequests,
  seedCoordinators,
  seedGroups,
} from "@/lib/operator-data";
import type { Booking, BookingStatus, PaymentStatus } from "@/types/operator";
import StatusBadge from "@/components/operator/status-badge";
import { formatINR } from "@/lib/pricing";

const bookingStatuses: BookingStatus[] = ["pending", "confirmed", "in-progress", "completed", "cancelled"];
const paymentStatuses: PaymentStatus[] = ["unpaid", "partial", "paid", "refunded"];

export default function OperatorBookingDetailPage() {
  const params = useParams<{ id: string }>();
  const [booking, setBooking] = useState<Booking | null | undefined>(undefined);

  useEffect(() => {
    const found = loadBookings().find((b) => b.id === params.id);
    setBooking(found ?? null);
  }, [params.id]);

  if (booking === undefined) return null;

  if (!booking) {
    return (
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-gray-500">Booking not found.</p>
        <Link href="/operator/bookings" className="mt-4 inline-block text-sm font-semibold text-primary">
          ← Back to bookings
        </Link>
      </div>
    );
  }

  const changeRequests = loadChangeRequests().filter((c) => c.bookingId === booking.id);
  const coordinator = seedCoordinators.find((c) => c.id === booking.coordinatorId);
  const group = seedGroups.find((g) => g.id === booking.groupId);

  const applyPatch = (patch: Partial<Booking>) => {
    const updated = updateBooking(booking.id, patch);
    setBooking(updated.find((b) => b.id === booking.id) ?? null);
  };

  return (
    <div className="mx-auto max-w-4xl">
      <Link href="/operator/bookings" className="flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-dark">
        <ArrowLeft className="h-4 w-4" /> Back to Bookings
      </Link>

      <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-2xl font-bold text-dark">{booking.customerName}</h1>
          <p className="mt-1 flex items-center gap-1 text-sm text-gray-500">
            <Mail className="h-3.5 w-3.5" /> {booking.customerEmail}
          </p>
        </div>
        <div className="flex gap-2">
          <StatusBadge status={booking.status} />
          <StatusBadge status={booking.paymentStatus} />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-400">Trip Details</h2>
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-600">
              <span className="flex items-center gap-1.5">
                <MapPin className="h-4 w-4 text-gray-400" /> {booking.destination}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4 text-gray-400" /> {booking.startDate} – {booking.endDate}
              </span>
              <span className="flex items-center gap-1.5">
                <Users className="h-4 w-4 text-gray-400" /> {booking.travelers} traveler{booking.travelers === 1 ? "" : "s"}
              </span>
            </div>

            <div className="mt-5 space-y-2 border-t border-gray-50 pt-4">
              {booking.costBreakdown.map((item) => (
                <div key={item.label} className="flex justify-between text-sm">
                  <span className="text-gray-500">{item.label}</span>
                  <span className="font-medium text-dark">{formatINR(item.amount)}</span>
                </div>
              ))}
              <div className="flex justify-between border-t border-gray-100 pt-2 text-sm font-bold text-dark">
                <span>Total</span>
                <span>{formatINR(booking.totalCost)}</span>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-400">Itinerary Change Requests</h2>
            {changeRequests.length === 0 ? (
              <p className="mt-3 text-sm text-gray-400">No change requests for this booking.</p>
            ) : (
              <div className="mt-3 space-y-3">
                {changeRequests.map((c) => (
                  <div key={c.id} className="rounded-2xl border border-gray-100 p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-dark">{c.reason}</p>
                      <StatusBadge status={c.status} />
                    </div>
                    <p className="mt-1 text-xs text-gray-500">{c.impact}</p>
                    <p className="mt-1 text-xs text-primary">Suggested: {c.suggestedResolution}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-400">Update Status</h2>
            <label className="mt-3 block text-xs font-medium text-gray-500">Booking Status</label>
            <select
              value={booking.status}
              onChange={(e) => applyPatch({ status: e.target.value as BookingStatus })}
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm capitalize focus:border-dark focus:outline-none"
            >
              {bookingStatuses.map((s) => (
                <option key={s} value={s}>
                  {s.replace("-", " ")}
                </option>
              ))}
            </select>

            <label className="mt-4 block text-xs font-medium text-gray-500">Payment Status</label>
            <select
              value={booking.paymentStatus}
              onChange={(e) => applyPatch({ paymentStatus: e.target.value as PaymentStatus })}
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm capitalize focus:border-dark focus:outline-none"
            >
              {paymentStatuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-400">Operations</h2>
            <div className="mt-3 space-y-3 text-sm">
              <div>
                <p className="text-xs text-gray-400">Coordinator</p>
                <p className="font-medium text-dark">{coordinator ? coordinator.name : "Unassigned"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Tour Group</p>
                <p className="font-medium text-dark">{group ? group.name : "Not grouped"}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
