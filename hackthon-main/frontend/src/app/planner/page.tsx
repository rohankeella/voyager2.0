"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence, Reorder } from "framer-motion";
import Link from "next/link";
import { Calendar, MapPin, Users, DollarSign, Save, Share2, Download, Plus, CreditCard } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import DayCard from "@/components/planner/day-card";
import FlightSearch from "@/components/planner/flight-search";
import { destinations } from "@/lib/mock-data";
import type { Trip, TripDay } from "@/types/trip";
import { activityTypeEmojis } from "@/types/trip";
import { loadTripById, upsertTrip, createBlankTrip } from "@/lib/trip-storage";
import { cn } from "@/lib/utils";

const durationOptions = [
  { value: 1, label: "1 Day" },
  { value: 2, label: "2 Days" },
  { value: 3, label: "3 Days" },
  { value: 4, label: "4 Days" },
  { value: 5, label: "5 Days" },
  { value: 7, label: "7 Days" },
  { value: 10, label: "10 Days" },
  { value: 14, label: "14 Days" },
];

const budgetOptions = [
  { value: "budget", label: "Budget ($50-100/day)" },
  { value: "comfortable", label: "Comfortable ($100-200/day)" },
  { value: "premium", label: "Premium ($200-400/day)" },
  { value: "luxury", label: "Luxury ($400+/day)" },
];

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

function formatDateDisplay(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function PlannerContent() {
  const searchParams = useSearchParams();
  const tripId = searchParams.get("tripId");

  const [trip, setTrip] = useState<Trip>(() => createBlankTrip());
  const [step, setStep] = useState<"setup" | "plan">("setup");
  const [saved, setSaved] = useState(false);
  const [showShare, setShowShare] = useState(false);

  // Load the requested trip (by ?tripId=) or start a brand new one. Each trip
  // keeps its own row in storage now, so opening one never overwrites another.
  useEffect(() => {
    if (tripId) {
      const existing = loadTripById(tripId);
      if (existing) {
        setTrip(existing);
        setStep(existing.days.length > 0 || existing.destination ? "plan" : "setup");
        return;
      }
    }
    setTrip(createBlankTrip());
    setStep("setup");
  }, [tripId]);

  // Auto-save this trip only (upsert by id) — other trips in storage are untouched.
  useEffect(() => {
    if (!trip.destination && !trip.name && trip.days.length === 0) return;
    upsertTrip(trip);
  }, [trip]);

  // Once the setup step is complete, the trip graduates from "draft" to "planned"
  // so it starts showing the lifecycle stepper on the dashboard.
  useEffect(() => {
    if (step === "plan") {
      setTrip((prev) => (!prev.status || prev.status === "draft" ? { ...prev, status: "planned" } : prev));
    }
  }, [step]);

  const handleDestinationSelect = (destinationId: string) => {
    const dest = destinations.find((d) => d.id === destinationId);
    if (dest) {
      setTrip((prev) => ({
        ...prev,
        destination: dest.name,
        destinationSlug: dest.slug,
      }));
    }
  };

  const handleDurationSelect = (days: number) => {
    const startDate = new Date(trip.startDate);
    const endDate = new Date(startDate);
    endDate.setDate(startDate.getDate() + days - 1);

    const newDays: TripDay[] = [];
    for (let i = 0; i < days; i++) {
      const dayDate = new Date(startDate);
      dayDate.setDate(startDate.getDate() + i);
      newDays.push({
        id: crypto.randomUUID(),
        date: formatDate(dayDate),
        title: `Day ${i + 1}`,
        activities: [],
      });
    }

    setTrip((prev) => ({
      ...prev,
      endDate: formatDate(endDate),
      days: newDays,
    }));
    setStep("plan");
  };

  const handleNameChange = (value: string) => {
    setTrip((prev) => ({ ...prev, name: value }));
  };

  const handleStartDateChange = (value: string) => {
    const days = trip.days.length;
    const startDate = new Date(value);
    const endDate = new Date(startDate);
    endDate.setDate(startDate.getDate() + days - 1);

    const newDays: TripDay[] = [];
    for (let i = 0; i < days; i++) {
      const dayDate = new Date(startDate);
      dayDate.setDate(startDate.getDate() + i);
      newDays.push({
        id: crypto.randomUUID(),
        date: formatDate(dayDate),
        title: `Day ${i + 1}`,
        activities: trip.days[i]?.activities || [],
      });
    }

    setTrip((prev) => ({
      ...prev,
      startDate: value,
      endDate: formatDate(endDate),
      days: days > 0 ? newDays : prev.days,
    }));
  };

  const handleReorderDays = (newDays: TripDay[]) => {
    const reindexed = newDays.map((day, index) => ({ ...day, title: `Day ${index + 1}` }));
    setTrip((prev) => ({ ...prev, days: reindexed }));
  };

  const handleUpdateDay = (updatedDay: TripDay) => {
    setTrip((prev) => ({
      ...prev,
      days: prev.days.map((d) => (d.id === updatedDay.id ? updatedDay : d)),
    }));
  };

  const handleRemoveDay = (dayId: string) => {
    const newDays = trip.days.filter((d) => d.id !== dayId);
    const reindexed = newDays.map((day, index) => ({ ...day, title: `Day ${index + 1}` }));
    const endDate = new Date(trip.startDate);
    endDate.setDate(new Date(trip.startDate).getDate() + reindexed.length - 1);
    setTrip((prev) => ({
      ...prev,
      days: reindexed,
      endDate: formatDate(endDate),
    }));
  };

  const handleAddDay = () => {
    const newDate = new Date(trip.endDate);
    newDate.setDate(newDate.getDate() + 1);
    const newDay: TripDay = {
      id: crypto.randomUUID(),
      date: formatDate(newDate),
      title: `Day ${trip.days.length + 1}`,
      activities: [],
    };
    setTrip((prev) => ({
      ...prev,
      days: [...prev.days, newDay],
      endDate: formatDate(newDate),
    }));
  };

  const handleSaveTrip = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleExportTrip = () => {
    const dataStr = JSON.stringify(trip, null, 2);
    const dataUri = "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);
    const exportFileAny = document.createElement("a");
    exportFileAny.href = dataUri;
    exportFileAny.download = `${trip.name || "trip"}-itinerary.json`;
    document.body.appendChild(exportFileAny);
    exportFileAny.click();
    document.body.removeChild(exportFileAny);
  };

  const handleShareTrip = () => {
    setShowShare(true);
    setTimeout(() => setShowShare(false), 3000);
  };

  const isSetupComplete = !!(trip.destination && trip.budget && trip.startDate && trip.days.length > 0);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <div className="mx-auto max-w-5xl px-4 pt-24 pb-12 sm:px-6 lg:px-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-bold text-dark sm:text-4xl">Trip Planner</h1>
          <p className="mt-2 text-gray-600">Build a custom day-by-day itinerary for your next adventure</p>
        </motion.div>

        <AnimatePresence mode="wait">
          {step === "setup" ? (
            <motion.div key="setup" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <SetupForm
                trip={trip}
                onNameChange={handleNameChange}
                onDestinationSelect={handleDestinationSelect}
                onStartDateChange={handleStartDateChange}
                onDurationSelect={handleDurationSelect}
                onBudgetSelect={(budget) => setTrip((prev) => ({ ...prev, budget }))}
                onTravelersChange={(travelers) => setTrip((prev) => ({ ...prev, travelers }))}
                onNext={() => setStep("plan")}
                canProceed={!!(trip.destination && trip.budget && trip.startDate)}
              />
            </motion.div>
          ) : (
            <motion.div key="plan" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <PlanView
                trip={trip}
                onUpdateDay={handleUpdateDay}
                onRemoveDay={handleRemoveDay}
                onReorderDays={handleReorderDays}
                onAddDay={handleAddDay}
                onSave={handleSaveTrip}
                onExport={handleExportTrip}
                onShare={handleShareTrip}
                saved={saved}
                isSetupComplete={isSetupComplete}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function PlannerPage() {
  return (
    <Suspense fallback={null}>
      <PlannerContent />
    </Suspense>
  );
}

type SetupProps = {
  trip: Trip;
  onNameChange: (value: string) => void;
  onDestinationSelect: (id: string) => void;
  onStartDateChange: (value: string) => void;
  onDurationSelect: (days: number) => void;
  onBudgetSelect: (budget: string) => void;
  onTravelersChange: (travelers: number) => void;
  onNext: () => void;
  canProceed: boolean;
};

function SetupForm({ trip, onNameChange, onDestinationSelect, onStartDateChange, onDurationSelect, onBudgetSelect, onTravelersChange, onNext, canProceed }: SetupProps) {
  return (
    <div className="space-y-8">
      <div>
        <label className="block text-sm font-medium text-dark mb-2">Trip Name</label>
        <input
          type="text"
          value={trip.name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="e.g. Bali Adventure 2024"
          className="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-dark outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-dark mb-3">Destination</label>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {destinations.map((d) => (
            <button
              key={d.id}
              onClick={() => onDestinationSelect(d.id)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-2xl border-2 p-3 text-center transition-all",
                trip.destinationSlug === d.slug ? "border-primary bg-primary/5" : "border-gray-100 hover:border-gray-200"
              )}
            >
              <span className="text-2xl">{activityTypeEmojis.sightseeing}</span>
              <span className="text-sm font-medium text-dark">{d.name}</span>
              <span className="text-xs text-gray-500">{d.country}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-dark mb-2">Start Date</label>
          <input
            type="date"
            value={trip.startDate}
            onChange={(e) => onStartDateChange(e.target.value)}
            className="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-dark outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-dark mb-2">Trip Duration</label>
          <div className="grid grid-cols-3 gap-2">
            {durationOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => onDurationSelect(option.value)}
                className={cn(
                  "rounded-xl border-2 px-3 py-2 text-center text-sm font-medium transition-all",
                  trip.days.length === option.value
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-dark mb-2">Budget Level</label>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {budgetOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => onBudgetSelect(option.value)}
              className={cn(
                "flex items-center justify-center gap-2 rounded-xl border-2 px-4 py-3 text-center text-sm font-medium transition-all",
                trip.budget === option.value
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
              )}
            >
              <DollarSign className="h-4 w-4" />
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-dark mb-2">Travelers</label>
        <div className="flex gap-2">
          <button
            onClick={() => onTravelersChange(Math.max(1, trip.travelers - 1))}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-gray-200 bg-white text-lg font-medium text-dark transition-colors hover:bg-gray-50"
            aria-label="Decrease travelers"
          >
            -
          </button>
          <div className="flex h-9 flex-1 items-center justify-center rounded-xl border border-gray-200 bg-white px-4 text-dark">
            {trip.travelers} {trip.travelers === 1 ? "Person" : "People"}
          </div>
          <button
            onClick={() => onTravelersChange(trip.travelers + 1)}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-gray-200 bg-white text-lg font-medium text-dark transition-colors hover:bg-gray-50"
            aria-label="Increase travelers"
          >
            +
          </button>
        </div>
      </div>

      <div className="pt-4">
        <motion.button
          whileHover={{ scale: canProceed ? 1.02 : 1 }}
          whileTap={{ scale: canProceed ? 0.98 : 1 }}
          onClick={onNext}
          disabled={!canProceed}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors",
            canProceed
              ? "bg-primary hover:bg-primary/90"
              : "bg-gray-200"
          )}
        >
          Start Planning
        </motion.button>
      </div>
    </div>
  );
}

type PlanProps = {
  trip: Trip;
  onUpdateDay: (day: TripDay) => void;
  onRemoveDay: (dayId: string) => void;
  onReorderDays: (days: TripDay[]) => void;
  onAddDay: () => void;
  onSave: () => void;
  onExport: () => void;
  onShare: () => void;
  saved: boolean;
  isSetupComplete: boolean;
};

function PlanView({ trip, onUpdateDay, onRemoveDay, onReorderDays, onAddDay, onSave, onExport, onShare, saved, isSetupComplete }: PlanProps) {
  const totalActivities = trip.days.reduce((sum, day) => sum + day.activities.length, 0);

  return (
    <>
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold text-dark">{trip.name || "Unnamed Trip"}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <MapPin className="h-4 w-4" />
              {trip.destination || "Select a destination"}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {formatDateDisplay(trip.startDate)} - {formatDateDisplay(trip.endDate)}
            </span>
            <span className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              {trip.travelers} {trip.travelers === 1 ? "traveler" : "travelers"}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link
            href={`/booking?tripId=${trip.id}`}
            className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
          >
            <CreditCard className="h-4 w-4" />
            Proceed to Book
          </Link>
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={onSave}
            className="flex items-center gap-2 rounded-full bg-green-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-600"
          >
            <Save className="h-4 w-4" />
            {saved ? "Saved!" : "Save Trip"}
          </motion.button>
          <button
            onClick={onExport}
            className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-dark transition-colors hover:bg-gray-50"
            aria-label="Export itinerary"
          >
            <Download className="h-4 w-4" />
            Export
          </button>
          <button
            onClick={onShare}
            className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-dark transition-colors hover:bg-gray-50"
            aria-label="Share itinerary"
          >
            <Share2 className="h-4 w-4" />
            Share
          </button>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-3 gap-4 rounded-2xl border border-gray-100 bg-white p-4 sm:grid-cols-6">
        <div className="text-center">
          <p className="text-2xl font-bold text-dark">{trip.days.length}</p>
          <p className="text-xs text-gray-500">Days</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-primary">{totalActivities}</p>
          <p className="text-xs text-gray-500">Activities</p>
        </div>
        <div className="text-center sm:col-span-2">
          <p className="text-2xl font-bold text-secondary">{trip.budget || "Not set"}</p>
          <p className="text-xs text-gray-500">Budget</p>
        </div>
        <div className="text-center sm:col-span-2">
          <p className="text-sm font-semibold text-dark">{trip.name || "Untitled"}</p>
          <p className="text-xs text-gray-500">Trip Name</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-accent">${trip.budget}</p>
          <p className="text-xs text-gray-500">Level</p>
        </div>
      </div>

      <div className="mb-6">
        <FlightSearch
          defaultDestination={trip.destination}
          defaultDepartureDate={trip.startDate}
          defaultAdults={trip.travelers}
        />
      </div>

      {trip.days.length > 0 ? (
        <Reorder.Group axis="y" values={trip.days} onReorder={onReorderDays} className="space-y-4">
          {trip.days.map((day, index) => (
            <Reorder.Item key={day.id} value={day} className="list-none">
              <DayCard day={day} dayIndex={index} onUpdate={onUpdateDay} onRemove={onRemoveDay} />
            </Reorder.Item>
          ))}
        </Reorder.Group>
      ) : (
        <motion.div className="py-12 text-center">
          <Calendar className="mx-auto mb-4 h-12 w-12 text-gray-300" />
          <p className="text-gray-500">No days added yet.</p>
          <p className="mt-1 text-sm text-gray-400">Select destination and duration to start planning</p>
        </motion.div>
      )}

      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={onAddDay}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-full border-2 border-dashed border-gray-200 bg-white py-3 text-sm font-medium text-gray-600 transition-colors hover:border-primary hover:text-primary"
      >
        <Plus className="h-5 w-5" />
        Add Day
      </motion.button>
    </>
  );
}
