"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { TripStyle, OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const options: { value: TripStyle; label: string; description: string }[] = [
  { value: "solo", label: "Solo", description: "Traveling alone" },
  { value: "couple", label: "Couple", description: "With a partner" },
  { value: "friends", label: "Friends", description: "Group of friends" },
  { value: "family", label: "Family", description: "With family members" },
  { value: "group", label: "Group", description: "Organized group tour" },
  { value: "business-leisure", label: "Business + Leisure", description: "Work trip with some fun" },
];

type Props = {
  data: { tripStyle: TripStyle | "" };
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step2({ data, save, onNext }: Props) {
  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">What&apos;s your ideal trip style?</h2>
        <p className="mt-2 text-gray-600">Choose the one that fits most trips.</p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {options.map((option) => {
          const selected = data.tripStyle === option.value;
          return (
            <motion.button
              key={option.value}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => save({ tripStyle: option.value })}
              className={cn(
                "relative flex flex-col items-start gap-2 rounded-2xl border-2 p-5 text-left transition-all",
                selected ? "border-primary bg-primary/5" : "border-gray-100 bg-white hover:border-gray-200"
              )}
            >
              <p className="font-semibold text-dark">{option.label}</p>
              <p className="text-sm text-gray-500">{option.description}</p>
              {selected && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-primary"
                >
                  <Check className="h-4 w-4 text-white" />
                </motion.div>
              )}
            </motion.button>
          );
        })}
      </div>

      <div className="mt-auto pt-8">
        <button
          onClick={onNext}
          disabled={!data.tripStyle}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
