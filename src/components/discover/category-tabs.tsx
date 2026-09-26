"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { DestinationType } from "@/lib/mock-data";

type Category = {
  id: string;
  label: string;
  destinationType?: DestinationType;
};

const categories: Category[] = [
  { id: "all", label: "All Destinations" },
  { id: "trending", label: "Trending", destinationType: "cities" },
  { id: "beaches", label: "Beach Escapes", destinationType: "beaches" },
  { id: "mountains", label: "Mountain Adventures", destinationType: "mountains" },
  { id: "cities", label: "City Breaks", destinationType: "cities" },
  { id: "tropical", label: "Tropical Paradises", destinationType: "tropical" },
  { id: "snow", label: "Snow Destinations", destinationType: "snow" },
  { id: "budget", label: "Budget Adventures", destinationType: undefined },
  { id: "luxury", label: "Luxury Escapes", destinationType: undefined },
  { id: "hidden", label: "Hidden Gems", destinationType: undefined },
];

type Props = {
  selected: string;
  onSelect: (id: string) => void;
};

export default function CategoryTabs({ selected, onSelect }: Props) {
  return (
    <div className="mb-6 overflow-x-auto">
      <div className="flex min-w-max gap-2 pb-2">
        {categories.map((category, index) => {
          const isSelected = selected === category.id;
          return (
            <motion.button
              key={category.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => onSelect(category.id)}
              className={cn(
                "rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap transition-all",
                isSelected
                  ? "border-2 border-primary bg-primary/10 text-primary"
                  : "border border-gray-200 bg-white text-gray-600 hover:border-gray-300"
              )}
            >
              {category.label}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}

export type { Category };
export { categories };
