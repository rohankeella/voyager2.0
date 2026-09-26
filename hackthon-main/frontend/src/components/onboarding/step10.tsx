"use client";

import { motion } from "framer-motion";
import type { OnboardingData } from "@/types/onboarding";

type Props = {
  data: OnboardingData;
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step10({ data, save, onNext }: Props) {
  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">Final preferences</h2>
        <p className="mt-2 text-gray-600">Tell us anything else you&apos;d love from your next trip.</p>
      </div>

      <div className="mt-8 flex-1">
        <textarea
          value={data.additionalNotes}
          onChange={(e) => save({ ...data, additionalNotes: e.target.value })}
          placeholder="For example: I love hidden gems, avoid crowded tourist spots, prefer local guides..."
          className="h-64 w-full rounded-2xl border border-gray-200 bg-white p-4 text-sm shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div className="mt-auto pt-8">
        <button
          onClick={onNext}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Create My Travel Profile
        </button>
      </div>
    </div>
  );
}
