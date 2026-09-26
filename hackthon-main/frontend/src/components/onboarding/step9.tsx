"use client";

import { useState, useCallback } from "react";
import { motion, Reorder } from "framer-motion";
import { GripVertical } from "lucide-react";
import type { Priority, OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const allPriorities: { value: Priority; label: string }[] = [
  { value: "price", label: "Price" },
  { value: "weather", label: "Weather" },
  { value: "food", label: "Food" },
  { value: "safety", label: "Safety" },
  { value: "nature", label: "Nature" },
  { value: "culture", label: "Culture" },
  { value: "nightlife", label: "Nightlife" },
  { value: "adventure", label: "Adventure" },
  { value: "luxury", label: "Luxury" },
  { value: "accessibility", label: "Accessibility" },
];

type Props = {
  data: { priorities: Priority[] };
  save: (next: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function Step9({ data, save, onNext }: Props) {
  const [items, setItems] = useState<Priority[]>(data.priorities.length ? data.priorities : allPriorities.map((p) => p.value));

  const handleReorder = useCallback(
    (next: Priority[]) => {
      setItems(next);
      save({ priorities: next });
    },
    [save]
  );

  return (
    <div className="flex h-full flex-col">
      <div>
        <h2 className="text-2xl font-bold text-dark sm:text-3xl">What matters most when choosing a destination?</h2>
        <p className="mt-2 text-gray-600">Rank these factors by dragging them. Top = most important.</p>
      </div>

      <div className="mt-8 flex-1">
        <Reorder.Group axis="y" values={items} onReorder={handleReorder} className="space-y-2">
          {items.map((priority, index) => {
            const meta = allPriorities.find((p) => p.value === priority);
            if (!meta) return null;
            return (
              <Reorder.Item
                key={priority}
                value={priority}
                className="flex items-center gap-3 rounded-2xl border border-gray-100 bg-white p-4"
                whileDrag={{ scale: 1.01, boxShadow: "0 10px 30px rgba(0,0,0,0.08)" }}
              >
                <GripVertical className="h-5 w-5 text-gray-400" />
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                  {index + 1}
                </span>
                <span className="font-medium text-dark">{meta.label}</span>
              </Reorder.Item>
            );
          })}
        </Reorder.Group>
      </div>

      <div className="mt-auto pt-8">
        <button
          onClick={onNext}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
