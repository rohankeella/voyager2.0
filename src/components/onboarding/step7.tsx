"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { Season, OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const options: { value: Season; label: string; emoji: string }[] = [
  { value: "spring", label: "Spring", emoji: "🌸" },
  { value: "summer", label: "Summer", emoji: "☀️" },
  { value: "monsoon", label: "Monsoon", emoji: "🌧️" },
  { value: "autumn", label: "Autumn", emoji: "🍂" },
  { value: "winter", label: "Winter", emoji: "❄️" },
];

type Props = {
  data: { seasons: Season[] };
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step7({ data, save, onNext }: Props) {
  const toggle = (value: Season) => {
    const current = data.seasons;
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    save({ seasons: next });
  };

  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">When do you prefer to travel?</h2>
        <p className="mt-2 text-gray-600">Select all seasons you enjoy traveling in.</p>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {options.map((option) => {
          const selected = data.seasons.includes(option.value);
          return (
            <motion.button
              key={option.value}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => toggle(option.value)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-2xl border-2 p-5 text-center transition-all",
                selected ? "border-primary bg-primary/5" : "border-gray-100 bg-white hover:border-gray-200"
              )}
            >
              <span className="text-4xl">{option.emoji}</span>
              <span className="text-sm font-medium text-dark">{option.label}</span>
              {selected && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="flex h-5 w-5 items-center justify-center rounded-full bg-primary"
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
          disabled={data.seasons.length === 0}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
