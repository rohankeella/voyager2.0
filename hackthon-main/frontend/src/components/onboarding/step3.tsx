"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { Activity, OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const options: { value: Activity; label: string; emoji: string }[] = [
  { value: "hiking", label: "Hiking", emoji: "🥾" },
  { value: "beaches", label: "Beaches", emoji: "🏖️" },
  { value: "trekking", label: "Trekking", emoji: "⛰️" },
  { value: "scuba-diving", label: "Scuba Diving", emoji: "🤿" },
  { value: "skiing", label: "Skiing", emoji: "🎿" },
  { value: "museums", label: "Museums", emoji: "🏛️" },
  { value: "historical-places", label: "Historical Places", emoji: "🏺" },
  { value: "nightlife", label: "Nightlife", emoji: "🌃" },
  { value: "shopping", label: "Shopping", emoji: "🛍️" },
  { value: "food-tours", label: "Food Tours", emoji: "🍲" },
  { value: "photography", label: "Photography", emoji: "📷" },
  { value: "wildlife", label: "Wildlife", emoji: "🦁" },
  { value: "camping", label: "Camping", emoji: "⛺" },
  { value: "road-trips", label: "Road Trips", emoji: "🚗" },
  { value: "water-sports", label: "Water Sports", emoji: "🏄" },
  { value: "festivals", label: "Festivals", emoji: "🎉" },
];

type Props = {
  data: { activities: Activity[] };
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step3({ data, save, onNext }: Props) {
  const toggle = (value: Activity) => {
    const current = data.activities;
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    save({ activities: next });
  };

  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">What activities do you enjoy?</h2>
        <p className="mt-2 text-gray-600">Select all that interest you.</p>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {options.map((option) => {
          const selected = data.activities.includes(option.value);
          return (
            <motion.button
              key={option.value}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => toggle(option.value)}
              className={cn(
                "flex flex-col items-center justify-center gap-2 rounded-2xl border-2 p-4 text-center transition-all",
                selected ? "border-primary bg-primary/5" : "border-gray-100 bg-white hover:border-gray-200"
              )}
            >
              <span className="text-3xl">{option.emoji}</span>
              <span className="text-sm font-medium text-dark">{option.label}</span>
              {selected && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary"
                >
                  <Check className="h-3 w-3 text-white" />
                </motion.div>
              )}
            </motion.button>
          );
        })}
      </div>

      <div className="mt-auto pt-8">
        <button
          onClick={onNext}
          disabled={data.activities.length === 0}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
