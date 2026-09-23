"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Loader2, MapPin, Clock, Wallet, TrendingUp } from "lucide-react";
import type { OnboardingData } from "@/types/onboarding";
import { ApiError, subscribeToUpdates, type ApiScored, type MatchResponse } from "@/lib/api";
import { fetchExperienceMatches } from "@/lib/recommendations";

// Anchor points must line up with what backend/app/seed.py populates.
const SEEDED_CITIES: { name: string; lat: number; lng: number }[] = [
  { name: "Bali",   lat: -8.4095, lng: 115.1889 },
  { name: "Kyoto",  lat: 35.0116, lng: 135.7681 },
  { name: "Paris",  lat: 48.8566, lng: 2.3522 },
  { name: "Mumbai", lat: 19.0760, lng: 72.8777 },
];

function CategoryPill({ category }: { category: ApiScored["experience"]["category"] }) {
  const label = category[0] + category.slice(1).toLowerCase();
  return <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">{label}</span>;
}

function ExperienceCard({ item, index }: { item: ApiScored; index: number }) {
  const { experience, score, transit_mins, distance_km, reasons } = item;
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="flex flex-col gap-3 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <CategoryPill category={experience.category} />
          <h3 className="mt-2 text-base font-semibold text-dark">{experience.title}</h3>
        </div>
        <div className="text-right">
          <div className="flex items-center justify-end gap-1 text-lg font-bold text-primary">
            <TrendingUp className="h-4 w-4" />
            {score.toFixed(0)}
          </div>
          <div className="text-[10px] uppercase tracking-wide text-gray-400">match</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
        <div className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {distance_km.toFixed(1)} km</div>
        <div className="flex items-center gap-1"><Clock className="h-3 w-3" /> {transit_mins} + {experience.duration_mins}m</div>
        <div className="flex items-center gap-1"><Wallet className="h-3 w-3" /> {experience.base_cost === 0 ? "Free" : `${experience.currency} ${experience.base_cost.toFixed(0)}`}</div>
      </div>

      {reasons.length > 0 && (
        <ul className="mt-1 space-y-1 border-t border-gray-100 pt-3 text-xs text-gray-500">
          {reasons.slice(0, 3).map((r, i) => <li key={i}>• {r}</li>)}
        </ul>
      )}
    </motion.article>
  );
}

export default function LiveExperienceMatches({
  preferences,
  defaultCity = "Bali",
  hoursOfWindow = 3,
}: {
  preferences: OnboardingData;
  defaultCity?: string;
  hoursOfWindow?: number;
}) {
  const [city, setCity] = useState(defaultCity);
  const [data, setData] = useState<MatchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const location = useMemo(
    () => SEEDED_CITIES.find((c) => c.name === city) ?? SEEDED_CITIES[0],
    [city],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const at = new Date();
    const windowEnd = new Date(at.getTime() + hoursOfWindow * 60 * 60 * 1000);
    fetchExperienceMatches(preferences, { lat: location.lat, lng: location.lng, city: location.name }, { at, windowEnd })
      .then((res) => { if (!cancelled) setData(res); })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError) setError(`Backend error (${err.status}): ${err.message}`);
        else setError("Couldn't reach the backend. Is it running on port 8000?");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [preferences, location, hoursOfWindow, reloadTick]);

  // F-06: silently refresh when the catalog changes.
  useEffect(() => {
    return subscribeToUpdates((event) => {
      if (event && typeof event === "object" && "type" in event && event.type === "catalog:changed") {
        setReloadTick((n) => n + 1);
      }
    });
  }, []);

  return (
    <section className="mt-16">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-dark">Live experience matches</h2>
          <p className="mt-1 text-sm text-gray-600">
            Personalised for your preferences in a {hoursOfWindow}-hour window — scored by the backend matching engine.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <label htmlFor="live-city" className="text-gray-500">City</label>
          <select
            id="live-city"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm text-dark focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            {SEEDED_CITIES.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
          </select>
        </div>
      </div>

      {loading && (
        <div className="flex items-center gap-2 rounded-2xl border border-gray-100 bg-white p-6 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Scoring experiences…
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {data && !loading && !error && (
        <>
          <p className="mb-3 text-xs text-gray-500">
            Scanned {data.candidates_scanned} candidates · returned {data.results.length} · window {data.query_window_mins} min
          </p>
          {data.results.length === 0 ? (
            <div className="rounded-2xl border border-gray-100 bg-white p-6 text-sm text-gray-500">
              No experiences fit this window. Try a longer window or a different city.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.results.map((item, i) => (
                <ExperienceCard key={item.experience.id} item={item} index={i} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
