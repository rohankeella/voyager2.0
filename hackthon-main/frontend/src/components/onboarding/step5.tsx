"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { BudgetLevel, OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const options: { value: BudgetLevel; label: string; description: string; emoji: string }[] = [
  { value: "backpacker", label: "Backpacker", description: "Hostels and street food", emoji: "🎒" },
  { value: "budget", label: "Budget", description: "Affordable stays and local transport", emoji: "💰" },
  { value: "comfortable", label: "Comfortable", description: "Mid-range hotels and convenience", emoji: "🏨" },
  { value: "premium", label: "Premium", description: "Boutique stays and guided tours", emoji: "🌟" },
  { value: "luxury", label: "Luxury", description: "Five-star and exclusive experiences", emoji: "👑" },
];

type Props = {
  data: { budget: BudgetLevel | ""; customDailyBudget: number | "" };
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step5({ data, save, onNext }: Props) {
  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">What&apos;s your budget?</h2>
        <p className="mt-2 text-gray-600">Pick the style that fits your wallet.</p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {options.map((option) => {
          const selected = data.budget === option.value;
          return (
            <motion.button
              key={option.value}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => save({ budget: option.value, customDailyBudget: "" })}
              className={cn(
                "relative flex items-center gap-4 rounded-2xl border-2 p-4 text-left transition-all",
                selected ? "border-primary bg-primary/5" : "border-gray-100 bg-white hover:border-gray-200"
              )}
            >
              <span className="text-3xl">{option.emoji}</span>
              <div className="flex-1">
                <p className="font-semibold text-dark">{option.label}</p>
                <p className="text-sm text-gray-500">{option.description}</p>
              </div>
              {selected && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="flex h-6 w-6 items-center justify-center rounded-full bg-primary"
                >
                  <Check className="h-4 w-4 text-white" />
                </motion.div>
              )}
            </motion.button>
          );
        })}
      </div>

      <div className="mt-6">
        <label className="block text-sm font-medium text-dark">Custom approximate daily budget (optional)</label>
        <input
          type="number"
          min={0}
          value={data.customDailyBudget === "" ? "" : data.customDailyBudget}
          onChange={(e) =>
            save({
              budget: data.budget,
              customDailyBudget: e.target.value === "" ? "" : Number(e.target.value),
            })
          }
          placeholder="e.g. 150"
          className="mt-1.5 block w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div className="mt-auto pt-8">
        <button
          onClick={onNext}
          disabled={!data.budget}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
