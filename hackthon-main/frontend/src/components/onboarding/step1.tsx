"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { TravelerType, OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const options: { value: TravelerType; label: string; description: string; emoji: string }[] = [
  { value: "adventure-seeker", label: "Adventure Seeker", description: "Thrills, hikes, and adrenaline", emoji: "🧗" },
  { value: "relaxation-lover", label: "Relaxation Lover", description: "Beaches, spas, and calm", emoji: "🌴" },
  { value: "culture-explorer", label: "Culture Explorer", description: "Museums, history, and traditions", emoji: "🏛️" },
  { value: "foodie", label: "Foodie", description: "Local cuisine and food tours", emoji: "🍜" },
  { value: "nature-lover", label: "Nature Lover", description: "Forests, wildlife, and outdoors", emoji: "🌿" },
  { value: "luxury-traveler", label: "Luxury Traveler", description: "Premium stays and fine dining", emoji: "✨" },
  { value: "budget-traveler", label: "Budget Traveler", description: "Value and affordable experiences", emoji: "🎒" },
  { value: "digital-nomad", label: "Digital Nomad", description: "Work remotely while traveling", emoji: "💻" },
];

type Props = {
  data: { travelerTypes: TravelerType[] };
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step1({ data, save, onNext }: Props) {
  const toggle = (value: TravelerType) => {
    const current = data.travelerTypes;
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    save({ travelerTypes: next });
  };

  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">What kind of traveler are you?</h2>
        <p className="mt-2 text-gray-600">Select all that describe you best.</p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {options.map((option) => {
          const selected = data.travelerTypes.includes(option.value);
          return (
            <motion.button
              key={option.value}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => toggle(option.value)}
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

      <div className="mt-auto pt-8">
        <button
          onClick={onNext}
          disabled={data.travelerTypes.length === 0}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
