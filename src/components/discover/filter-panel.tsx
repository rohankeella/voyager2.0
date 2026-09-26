"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DestinationType, BudgetLevel, Season, Activity } from "@/lib/mock-data";

export type Filters = {
  destinationTypes: DestinationType[];
  budget: BudgetLevel[];
  season: Season[];
  activities: Activity[];
  minCost: number;
  maxCost: number;
};

type OptionGroup = {
  key: keyof Filters;
  label: string;
  options: { value: string; label: string }[];
  type: "multi" | "range" | "cost";
};

const budgetOptions: { value: BudgetLevel; label: string }[] = [
  { value: "backpacker", label: "Backpacker" },
  { value: "budget", label: "Budget" },
  { value: "comfortable", label: "Comfortable" },
  { value: "premium", label: "Premium" },
  { value: "luxury", label: "Luxury" },
];

const seasonOptions: { value: Season; label: string }[] = [
  { value: "spring", label: "Spring" },
  { value: "summer", label: "Summer" },
  { value: "monsoon", label: "Monsoon" },
  { value: "autumn", label: "Autumn" },
  { value: "winter", label: "Winter" },
];

const activityOptions: { value: Activity; label: string }[] = [
  { value: "hiking", label: "Hiking" },
  { value: "beaches", label: "Beaches" },
  { value: "trekking", label: "Trekking" },
  { value: "scuba-diving", label: "Scuba Diving" },
  { value: "skiing", label: "Skiing" },
  { value: "museums", label: "Museums" },
  { value: "historical-places", label: "Historical Places" },
  { value: "nightlife", label: "Nightlife" },
  { value: "shopping", label: "Shopping" },
  { value: "food-tours", label: "Food Tours" },
  { value: "photography", label: "Photography" },
  { value: "wildlife", label: "Wildlife" },
];

const filterGroups: OptionGroup[] = [
  {
    key: "destinationTypes",
    label: "Destination Type",
    options: [
      { value: "beaches", label: "Beaches" },
      { value: "mountains", label: "Mountains" },
      { value: "cities", label: "Cities" },
      { value: "countryside", label: "Countryside" },
      { value: "islands", label: "Islands" },
      { value: "forests", label: "Forests" },
      { value: "deserts", label: "Deserts" },
      { value: "historical-cities", label: "Historical Cities" },
      { value: "tropical", label: "Tropical" },
      { value: "snow", label: "Snow Destinations" },
    ],
    type: "multi",
  },
  {
    key: "budget",
    label: "Budget Level",
    options: budgetOptions,
    type: "multi",
  },
  {
    key: "season",
    label: "Best Season",
    options: seasonOptions,
    type: "multi",
  },
  {
    key: "activities",
    label: "Activities",
    options: activityOptions,
    type: "multi",
  },
];

type Props = {
  filters: Filters;
  onChange: (filters: Filters) => void;
  onReset: () => void;
  activeCount: number;
};

export default function FilterPanel({ filters, onChange, onReset, activeCount }: Props) {
  const [openGroup, setOpenGroup] = useState<string | null>(null);

  const toggleValue = (key: keyof Filters, value: string) => {
    if (key === "minCost" || key === "maxCost") return;

    const current = filters[key] as string[];
    const newValue = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    onChange({ ...filters, [key]: newValue });
  };

  const setCostRange = (min: number, max: number) => {
    onChange({ ...filters, minCost: min, maxCost: max });
  };

  return (
    <div className="w-full space-y-3">
      {filterGroups.map((group) => {
        const isOpen = openGroup === group.key;
        const activeValues = (filters[group.key] as string[]) || [];

        return (
          <div key={group.key} className="border-b border-gray-100 pb-3">
            <button
              onClick={() => setOpenGroup(isOpen ? null : group.key)}
              className="flex w-full items-center justify-between text-left"
            >
              <span className="font-medium text-dark">{group.label}</span>
              <ChevronDown
                className={cn("h-4 w-4 text-gray-500 transition-transform", isOpen && "rotate-180")}
              />
            </button>

            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2, ease: "easeInOut" }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 flex flex-wrap gap-2">
                    {group.options.map((option) => {
                      const isSelected = activeValues.includes(option.value);
                      return (
                        <motion.button
                          key={option.value}
                          whileHover={{ scale: 1.03 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={() => toggleValue(group.key, option.value)}
                          className={cn(
                            "rounded-full px-3.5 py-1.5 text-xs font-medium transition-all",
                            isSelected
                              ? "border-2 border-primary bg-primary/10 text-primary"
                              : "border border-gray-200 bg-white text-gray-600 hover:border-gray-300"
                          )}
                        >
                          {option.label}
                        </motion.button>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}

      <div className="border-b border-gray-100 pb-3">
        <button
          onClick={() => setOpenGroup(openGroup === "cost" ? null : "cost")}
          className="flex w-full items-center justify-between text-left"
        >
          <span className="font-medium text-dark">Daily Cost Range</span>
          <ChevronDown
            className={cn("h-4 w-4 text-gray-500 transition-transform", openGroup === "cost" && "rotate-180")}
          />
        </button>

        <AnimatePresence initial={false}>
          {openGroup === "cost" && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="mt-3 space-y-3"
            >
              <div className="flex items-center gap-2 text-sm">
                <span className="w-12 text-dark">${filters.minCost}</span>
                <input
                  type="range"
                  min={0}
                  max={500}
                  step={10}
                  value={filters.minCost}
                  onChange={(e) => setCostRange(Number(e.target.value), filters.maxCost)}
                  className="flex-1 cursor-pointer accent-primary"
                />
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="w-12 text-dark">${filters.maxCost}</span>
                <input
                  type="range"
                  min={0}
                  max={500}
                  step={10}
                  value={filters.maxCost}
                  onChange={(e) => setCostRange(filters.minCost, Number(e.target.value))}
                  className="flex-1 cursor-pointer accent-primary"
                />
              </div>
              <div className="flex justify-between text-xs text-gray-500">
                <span>$0</span>
                <span>$500</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {activeCount > 0 && (
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={onReset}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
        >
          <X className="h-4 w-4" />
          Clear all filters ({activeCount})
        </motion.button>
      )}
    </div>
  );
}
