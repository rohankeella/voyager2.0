"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { MapPin, Calendar, Users, Wallet, ArrowRight, Smartphone } from "lucide-react";
import TripCard from "@/components/dashboard/trip-card";
import AIAssistantPanel from "@/components/dashboard/ai-assistant-panel";
import NotificationsPanel from "@/components/dashboard/notifications-panel";
import RecommendationCard from "@/components/dashboard/recommendation-card";
import { destinations } from "@/lib/mock-data";
import { loadTrips } from "@/lib/trip-storage";
import type { Trip } from "@/types/trip";

const recommendedSlugs = ["bali", "swiss-alps", "kerala", "tokyo"];
const recommended = destinations.filter((d) => recommendedSlugs.includes(d.slug));

const steps = [
  { number: 1, title: "Tell Us Your Preferences", description: "Destination, dates, budget, interests" },
  { number: 2, title: "Get Personalized Plan", description: "AI creates and optimizes your itinerary" },
  { number: 3, title: "Book & Travel", description: "Confirm, pay and get real-time support" },
];

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function DashboardHome() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [destination, setDestination] = useState("");
  const [travelers, setTravelers] = useState(2);
  const [budget, setBudget] = useState("");

  useEffect(() => {
    setTrips(loadTrips());
  }, []);

  return (
    <div className="mx-auto max-w-7xl">
      {/* Greeting + quick plan bar */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="overflow-hidden rounded-3xl bg-gradient-to-br from-primary/10 via-white to-secondary/10 p-6 sm:p-8"
      >
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <h1 className="text-2xl font-bold text-dark sm:text-3xl">{greeting()}, Rohan! 👋</h1>
            <p className="mt-1 text-gray-600">Where do you want to go next?</p>
          </div>
          <p className="hidden max-w-[220px] text-right font-serif text-sm italic text-gray-400 lg:block">
            &ldquo;Collect moments, not things&rdquo;
          </p>
        </div>

        <form
          onSubmit={(e) => e.preventDefault()}
          className="mt-6 flex flex-col gap-3 rounded-2xl border border-gray-100 bg-white p-3 shadow-sm lg:flex-row lg:items-center"
        >
          <label className="flex flex-1 items-center gap-2.5 rounded-xl px-3 py-2 lg:border-r lg:border-gray-100">
            <MapPin className="h-4 w-4 shrink-0 text-gray-400" />
            <span className="w-full">
              <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400">Destination</span>
              <input
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="Search destination"
                className="w-full border-0 p-0 text-sm text-dark placeholder:text-gray-400 focus:outline-none focus:ring-0"
              />
            </span>
          </label>

          <label className="flex flex-1 items-center gap-2.5 rounded-xl px-3 py-2 lg:border-r lg:border-gray-100">
            <Calendar className="h-4 w-4 shrink-0 text-gray-400" />
            <span className="w-full">
              <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400">Dates</span>
              <input
                type="text"
                onFocus={(e) => (e.target.type = "date")}
                placeholder="Select dates"
                className="w-full border-0 p-0 text-sm text-dark placeholder:text-gray-400 focus:outline-none focus:ring-0"
              />
            </span>
          </label>

          <label className="flex flex-1 items-center gap-2.5 rounded-xl px-3 py-2 lg:border-r lg:border-gray-100">
            <Users className="h-4 w-4 shrink-0 text-gray-400" />
            <span className="w-full">
              <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400">Travelers</span>
              <select
                value={travelers}
                onChange={(e) => setTravelers(Number(e.target.value))}
                className="w-full border-0 bg-transparent p-0 text-sm text-dark focus:outline-none focus:ring-0"
              >
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <option key={n} value={n}>
                    {n} Traveler{n > 1 ? "s" : ""}
                  </option>
                ))}
              </select>
            </span>
          </label>

          <label className="flex flex-1 items-center gap-2.5 rounded-xl px-3 py-2">
            <Wallet className="h-4 w-4 shrink-0 text-gray-400" />
            <span className="w-full">
              <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400">Budget (Optional)</span>
              <input
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="₹ Budget"
                className="w-full border-0 p-0 text-sm text-dark placeholder:text-gray-400 focus:outline-none focus:ring-0"
              />
            </span>
          </label>

          <Link
            href="/planner"
            className="flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
          >
            Plan My Trip <ArrowRight className="h-4 w-4" />
          </Link>
        </form>
      </motion.div>

      <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Main column */}
        <div className="space-y-8 xl:col-span-2">
          <section>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-dark">My Trips</h2>
              <Link href="/dashboard/trips" className="text-sm font-semibold text-primary hover:text-primary/80">
                View All →
              </Link>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {trips.slice(0, 3).map((trip, i) => (
                <TripCard key={trip.id} trip={trip} index={i} />
              ))}
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-dark">Recommended for You</h2>
              <Link href="/discover" className="text-sm font-semibold text-primary hover:text-primary/80">
                View All →
              </Link>
            </div>
            <p className="mt-1 text-sm text-gray-500">Based on your interests, travel style and past trips</p>
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {recommended.map((d) => (
                <RecommendationCard key={d.id} destination={d} />
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-bold text-dark">Plan Your Trip in 3 Easy Steps</h2>
              <p className="text-sm text-gray-500">From idea to adventure, we&rsquo;ve got you covered</p>
            </div>
            <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-3">
              {steps.map((step) => (
                <div key={step.number} className="flex items-start gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                    {step.number}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-dark">{step.title}</p>
                    <p className="mt-0.5 text-xs text-gray-500">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right rail */}
        <div className="space-y-6">
          <AIAssistantPanel />
          <NotificationsPanel />

          <div className="overflow-hidden rounded-3xl bg-gradient-to-br from-dark to-dark/80 p-6 text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10">
              <Smartphone className="h-4 w-4" />
            </span>
            <p className="mt-3 text-base font-bold leading-snug">Stay on track wherever you go.</p>
            <p className="mt-1.5 text-xs text-white/70">
              Get real-time updates, maps, and support during your trip.
            </p>
            <Link
              href="/dashboard/assistant"
              className="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-full bg-white px-4 py-2.5 text-xs font-semibold text-dark transition-colors hover:bg-white/90"
            >
              Open Live Trip <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
