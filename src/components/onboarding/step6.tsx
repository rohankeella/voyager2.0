"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { TripDuration, OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const options: { value: TripDuration; label: string }[] = [
  { value: "weekend", label: "Weekend" },
  { value: "3-5-days", label: "3–5 days" },
  { value: "1-week", label: "1 week" },
  { value: "1-2-weeks", label: "1–2 weeks" },
  { value: "2-4-weeks", label: "2–4 weeks" },
  { value: "1-month-plus", label: "1+ month" },
];

type Props = {
  data: { duration: TripDuration | "" };
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step6({ data, save, onNext }: Props) {
  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">How long do you usually travel?</h2>
        <p className="mt-2 text-gray-600">Pick your typical trip length.</p>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {options.map((option) => {
          const selected = data.duration === option.value;
          return (
            <motion.button
              key={option.value}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => save({ duration: option.value })}
              className={cn(
                "flex items-center justify-center rounded-2xl border-2 p-4 text-base font-medium transition-all",
                selected ? "border-primary bg-primary/5 text-primary" : "border-gray-100 bg-white text-dark hover:border-gray-200"
              )}
            >
              {option.label}
              {selected && (
                <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} className="ml-2">
                  <Check className="h-4 w-4 text-primary" />
                </motion.span>
              )}
            </motion.button>
          );
        })}
      </div>

      <div className="mt-auto pt-8">
        <button
          onClick={onNext}
          disabled={!data.duration}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
