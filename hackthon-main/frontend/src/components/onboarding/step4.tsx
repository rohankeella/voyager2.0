"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { DestinationType, OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const options: { value: DestinationType; label: string; emoji: string }[] = [
  { value: "beaches", label: "Beaches", emoji: "🏖️" },
  { value: "mountains", label: "Mountains", emoji: "🏔️" },
  { value: "cities", label: "Cities", emoji: "🏙️" },
  { value: "countryside", label: "Countryside", emoji: "🌾" },
  { value: "islands", label: "Islands", emoji: "🏝️" },
  { value: "forests", label: "Forests", emoji: "🌲" },
  { value: "deserts", label: "Deserts", emoji: "🏜️" },
  { value: "historical-cities", label: "Historical Cities", emoji: "🏛️" },
  { value: "tropical", label: "Tropical", emoji: "🌴" },
  { value: "snow", label: "Snow Destinations", emoji: "❄️" },
];

type Props = {
  data: { destinationTypes: DestinationType[] };
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step4({ data, save, onNext }: Props) {
  const toggle = (value: DestinationType) => {
    const current = data.destinationTypes;
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    save({ destinationTypes: next });
  };

  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">What kind of destinations attract you?</h2>
        <p className="mt-2 text-gray-600">Select all that appeal to you.</p>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {options.map((option) => {
          const selected = data.destinationTypes.includes(option.value);
          return (
            <motion.button
              key={option.value}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => toggle(option.value)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-2xl border-2 p-4 text-center transition-all",
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
          disabled={data.destinationTypes.length === 0}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
