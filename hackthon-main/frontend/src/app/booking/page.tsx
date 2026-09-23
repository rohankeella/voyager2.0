"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Calendar, MapPin, Users, ShieldCheck, Loader2 } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import HotelOffers from "@/components/booking/hotel-offers";
import type { Trip } from "@/types/trip";
import { loadTripById, loadTrips, updateTripStatus } from "@/lib/trip-storage";
import { BOOKINGS_STORAGE_KEY, type Booking } from "@/types/operator";
import { estimateTripCost, formatINR } from "@/lib/pricing";
import Link from "next/link";

function saveBooking(booking: Booking) {
  try {
    const raw = localStorage.getItem(BOOKINGS_STORAGE_KEY);
    const existing: Booking[] = raw ? JSON.parse(raw) : [];
    localStorage.setItem(BOOKINGS_STORAGE_KEY, JSON.stringify([...existing, booking]));
  } catch {
    // ignore
  }
}

function BookingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tripId = searchParams.get("tripId");
  const [trip, setTrip] = useState<Trip | null | undefined>(undefined);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (tripId) {
      setTrip(loadTripById(tripId) ?? null);
      return;
    }
    // No tripId given — fall back to the most recently created real trip, if any.
    const all = loadTrips().filter((t) => !t.id.startsWith("seed-"));
    setTrip(all.length > 0 ? all[all.length - 1] : null);
  }, [tripId]);

  if (trip === undefined) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-24 text-center">
          <h1 className="text-2xl font-bold text-dark">No trip ready to book yet</h1>
          <p className="mt-2 text-gray-500">
            Build an itinerary in the planner first — you&rsquo;ll come back here to review pricing and confirm.
          </p>
          <Link
            href="/onboarding"
            className="mt-6 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary/90"
          >
            Start Planning
          </Link>
        </div>
      </div>
    );
  }

  const estimate = estimateTripCost(trip);

  const handleConfirm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email) return;
    setIsProcessing(true);

    const booking: Booking = {
      id: `bk-${Date.now().toString().slice(-8)}`,
      tripId: trip.id,
      customerName: name,
      customerEmail: email,
      destination: trip.destination,
      startDate: trip.startDate,
      endDate: trip.endDate,
      travelers: trip.travelers,
      costBreakdown: estimate.breakdown,
      totalCost: estimate.total,
      status: "confirmed",
      paymentStatus: "paid",
      createdAt: new Date().toISOString(),
    };

    // Simulate a payment round-trip.
    setTimeout(() => {
      saveBooking(booking);
      updateTripStatus(trip.id, "booked");
      router.push(`/booking/confirmation?id=${booking.id}`);
    }, 900);
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        <h1 className="text-2xl font-bold text-dark sm:text-3xl">Review & Book</h1>
        <p className="mt-1 text-gray-500">Confirm your itinerary, check the price breakdown, and complete booking.</p>

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm"
            >
              <h2 className="text-lg font-bold text-dark">{trip.name || trip.destination}</h2>
              <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-gray-500">
                <span className="flex items-center gap-1">
                  <MapPin className="h-4 w-4" /> {trip.destination}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" /> {trip.startDate} – {trip.endDate}
                </span>
                <span className="flex items-center gap-1">
                  <Users className="h-4 w-4" /> {trip.travelers} traveler{trip.travelers === 1 ? "" : "s"}
                </span>
              </div>
              <p className="mt-3 text-sm text-gray-500">
                {estimate.days} day itinerary · {trip.days.length} day{trip.days.length === 1 ? "" : "s"} planned in detail
              </p>
            </motion.div>

            <HotelOffers
              city={trip.destination}
              checkIn={trip.startDate}
              checkOut={trip.endDate}
              adults={trip.travelers}
            />

            <form
              onSubmit={handleConfirm}
              className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm"
            >
              <h2 className="text-lg font-bold text-dark">Traveler Details</h2>
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label className="text-sm">
                  <span className="mb-1 block font-medium text-gray-700">Full Name</span>
                  <input
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    placeholder="Rohan Kapoor"
                  />
                </label>
                <label className="text-sm">
                  <span className="mb-1 block font-medium text-gray-700">Email</span>
                  <input
                    required
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    placeholder="you@example.com"
                  />
                </label>
                <label className="text-sm sm:col-span-2">
                  <span className="mb-1 block font-medium text-gray-700">Phone</span>
                  <input
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    placeholder="+91 98xxxxxxx"
                  />
                </label>
              </div>

              <button
                type="submit"
                disabled={isProcessing}
                className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-primary py-3.5 text-sm font-semibold text-white transition-colors hover:bg-primary/90 disabled:opacity-70"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Processing payment…
                  </>
                ) : (
                  <>Confirm & Pay {formatINR(estimate.total)}</>
                )}
              </button>
              <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-gray-400">
                <ShieldCheck className="h-3.5 w-3.5" /> This is a simulated payment for demo purposes.
              </p>
            </form>
          </div>

          <div className="h-fit rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-bold text-dark">Price Breakdown</h2>
            <div className="mt-4 space-y-3">
              {estimate.breakdown.map((item) => (
                <div key={item.label} className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">{item.label}</span>
                  <span className="font-medium text-dark">{formatINR(item.amount)}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4">
              <span className="text-sm font-semibold text-dark">Total</span>
              <span className="text-xl font-bold text-primary">{formatINR(estimate.total)}</span>
            </div>
            <p className="mt-2 text-xs text-gray-400">
              ≈ {formatINR(Math.round(estimate.total / trip.travelers))} per traveler
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function BookingPage() {
  return (
    <Suspense fallback={null}>
      <BookingContent />
    </Suspense>
  );
}
