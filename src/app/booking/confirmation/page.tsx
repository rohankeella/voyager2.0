"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, Calendar, MapPin, Users } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import { BOOKINGS_STORAGE_KEY, type Booking } from "@/types/operator";
import { formatINR } from "@/lib/pricing";

function loadBooking(id: string | null): Booking | null {
  if (!id) return null;
  try {
    const raw = localStorage.getItem(BOOKINGS_STORAGE_KEY);
    if (!raw) return null;
    const bookings: Booking[] = JSON.parse(raw);
    return bookings.find((b) => b.id === id) ?? null;
  } catch {
    return null;
  }
}

function BookingConfirmationContent() {
  const params = useSearchParams();
  const [booking, setBooking] = useState<Booking | null | undefined>(undefined);

  useEffect(() => {
    setBooking(loadBooking(params.get("id")));
  }, [params]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="mx-auto max-w-xl px-4 py-16 text-center sm:px-6">
        <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
          <CheckCircle2 className="h-8 w-8" />
        </span>
        <h1 className="mt-5 text-2xl font-bold text-dark sm:text-3xl">Booking Confirmed!</h1>
        <p className="mt-2 text-gray-500">
          Your trip is booked. A confirmation has been sent to your email, and your operator has been notified.
        </p>

        {booking && (
          <div className="mt-8 rounded-3xl border border-gray-100 bg-white p-6 text-left shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Booking ID</p>
              <p className="font-mono text-sm font-semibold text-dark">{booking.id}</p>
            </div>
            <div className="mt-4 space-y-2 text-sm text-gray-600">
              <p className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-gray-400" /> {booking.destination}
              </p>
              <p className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-gray-400" /> {booking.startDate} – {booking.endDate}
              </p>
              <p className="flex items-center gap-2">
                <Users className="h-4 w-4 text-gray-400" /> {booking.travelers} traveler{booking.travelers === 1 ? "" : "s"}
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4">
              <span className="text-sm font-semibold text-dark">Total Paid</span>
              <span className="text-lg font-bold text-primary">{formatINR(booking.totalCost)}</span>
            </div>
          </div>
        )}

        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            href="/dashboard/home"
            className="rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary/90"
          >
            Go to Dashboard
          </Link>
          <Link
            href="/dashboard/trips"
            className="rounded-full border border-gray-200 px-6 py-3 text-sm font-semibold text-dark hover:bg-gray-50"
          >
            View My Trips
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function BookingConfirmationPage() {
  return (
    <Suspense fallback={null}>
      <BookingConfirmationContent />
    </Suspense>
  );
}
