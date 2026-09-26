"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { emptyOnboardingData, type OnboardingData } from "@/types/onboarding";
import DestinationCard from "@/components/destinations/destination-card";
import LiveExperienceMatches from "@/components/destinations/live-experience-matches";
import { getTopDestinations } from "@/lib/recommendations";

const STORAGE_KEY = "voyager_onboarding_data";

export default function RecommendationsPage() {
  const [mounted, setMounted] = useState(false);
  const [preferences, setPreferences] = useState<OnboardingData>(emptyOnboardingData);
  const [destinations, setDestinations] = useState(getTopDestinations(emptyOnboardingData));

  useEffect(() => {
    setMounted(true);
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as OnboardingData;
        setPreferences(parsed);
        setDestinations(getTopDestinations(parsed));
      }
    } catch {
      // ignore
    }
  }, []);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-dark sm:text-4xl">Recommended for you</h1>
            <p className="mt-2 text-gray-600">Explore our handpicked destinations</p>
          </div>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {getTopDestinations(emptyOnboardingData).map((destination, index) => (
              <DestinationCard key={destination.id} destination={destination} index={index} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-bold text-dark sm:text-4xl">Recommended for you</h1>
          <p className="mt-2 text-gray-600">
            {destinations.length > 0 && destinations[0].matchScore
              ? `Top matches based on your preferences`
              : "Explore our handpicked destinations"}
          </p>
        </motion.div>

        {preferences.travelerTypes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 flex flex-wrap gap-2"
          >
            {preferences.activities.slice(0, 8).map((activity) => (
              <span
                key={activity}
                className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
              >
                {activity.replace("-", " ")}
              </span>
            ))}
          </motion.div>
        )}

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {destinations.map((destination, index) => (
            <DestinationCard key={destination.id} destination={destination} index={index} />
          ))}
        </div>

        {destinations.length === 0 && (
          <div className="mt-20 text-center">
            <p className="text-gray-500">No destinations found.</p>
          </div>
        )}

        <LiveExperienceMatches preferences={preferences} />
      </div>
    </div>
  );
}
