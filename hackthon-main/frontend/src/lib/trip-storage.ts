import { STORAGE_KEY, type Trip, type TripStatus } from "@/types/trip";
import { seedTrips } from "@/lib/dashboard-data";

function readTrips(): Trip[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((t): t is Trip => !!t && !!t.id) : [];
  } catch {
    return [];
  }
}

function writeTrips(trips: Trip[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trips));
  } catch {
    // ignore quota / serialization errors
  }
}

// Real trips (created via onboarding/planner) are always shown. Seed demo trips
// fill in any gaps so the dashboard isn't empty on a fresh install, and quietly
// drop out one-by-one as real trips take over the same id.
export function loadTrips(): Trip[] {
  const real = readTrips();
  const realIds = new Set(real.map((t) => t.id));
  return [...real, ...seedTrips.filter((t) => !realIds.has(t.id))];
}

export function loadTripById(id: string): Trip | undefined {
  return readTrips().find((t) => t.id === id) ?? seedTrips.find((t) => t.id === id);
}

// Insert or update a single trip without touching any other trip in storage.
export function upsertTrip(trip: Trip): Trip[] {
  const trips = readTrips();
  const idx = trips.findIndex((t) => t.id === trip.id);
  if (idx >= 0) {
    trips[idx] = trip;
  } else {
    trips.push(trip);
  }
  writeTrips(trips);
  return trips;
}

export function updateTripStatus(id: string, status: TripStatus): Trip[] {
  const existing = loadTripById(id);
  const base: Trip = existing ?? {
    id,
    name: "",
    destination: "",
    destinationSlug: "",
    startDate: "",
    endDate: "",
    budget: "",
    travelers: 1,
    days: [],
    createdAt: new Date().toISOString(),
  };
  return upsertTrip({ ...base, status });
}

export function deleteTrip(id: string): Trip[] {
  const trips = readTrips().filter((t) => t.id !== id);
  writeTrips(trips);
  return trips;
}

export function createBlankTrip(): Trip {
  return {
    id: crypto.randomUUID(),
    name: "",
    destination: "",
    destinationSlug: "",
    startDate: new Date().toISOString().split("T")[0],
    endDate: "",
    budget: "",
    travelers: 2,
    days: [],
    createdAt: new Date().toISOString(),
    status: "draft",
  };
}
