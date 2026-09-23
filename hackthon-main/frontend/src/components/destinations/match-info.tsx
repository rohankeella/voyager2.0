"use client";

import { motion } from "framer-motion";
import { Clock, DollarSign, Sun, Users, Heart } from "lucide-react";
import type { Destination, BudgetLevel, TripDuration, Activity } from "@/lib/mock-data";

type Props = {
  destination: Destination;
  matchScore?: number;
};

const budgetLabels: Record<BudgetLevel, string> = {
  backpacker: "Backpacker",
  budget: "Budget",
  comfortable: "Comfortable",
  premium: "Premium",
  luxury: "Luxury",
};

const durationLabels: Record<TripDuration, string> = {
  weekend: "Weekend",
  "3-5-days": "3–5 days",
  "1-week": "1 week",
  "1-2-weeks": "1–2 weeks",
  "2-4-weeks": "2–4 weeks",
  "1-month-plus": "1+ month",
};

const activityLabels: Record<Activity, string> = {
  hiking: "Hiking",
  beaches: "Beaches",
  trekking: "Trekking",
  "scuba-diving": "Scuba Diving",
  skiing: "Skiing",
  museums: "Museums",
  "historical-places": "Historical Places",
  nightlife: "Nightlife",
  shopping: "Shopping",
  "food-tours": "Food Tours",
  photography: "Photography",
  wildlife: "Wildlife",
  camping: "Camping",
  "road-trips": "Road Trips",
  "water-sports": "Water Sports",
  festivals: "Festivals",
};

export default function MatchInfo({ destination, matchScore }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="grid grid-cols-1 gap-4 rounded-2xl border border-gray-100 bg-white p-6 md:grid-cols-2 md:gap-6"
    >
      {matchScore !== undefined && (
        <motion.div className="flex items-center gap-4 rounded-xl bg-primary/5 p-4">
          <motion.div
            className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-xl font-bold text-white"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
          >
            {matchScore}%
          </motion.div>
          <div>
            <p className="text-sm font-medium text-gray-500">Match Score</p>
            <p className="text-lg font-bold text-dark">{matchScore}% match for your preferences</p>
          </div>
        </motion.div>
      )}

      <motion.div className="flex items-center gap-4 rounded-xl bg-gray-50 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
          <DollarSign className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Daily Budget</p>
          <p className="text-lg font-bold text-dark">{budgetLabels[destination.budget]}</p>
          <p className="text-sm text-gray-500">${destination.estimatedDailyCost}/day estimated</p>
        </div>
      </motion.div>

      <motion.div
        className="flex items-center gap-4 rounded-xl bg-gray-50 p-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
          <Clock className="h-5 w-5 text-secondary" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Recommended Duration</p>
          <p className="text-lg font-bold text-dark">{destination.recommendedDuration.map((d) => durationLabels[d]).join(" - ")}</p>
        </div>
      </motion.div>

      <motion.div
        className="flex items-center gap-4 rounded-xl bg-gray-50 p-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
          <Sun className="h-5 w-5 text-accent" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Best Seasons</p>
          <p className="text-lg font-bold text-dark capitalize">{destination.bestSeason.join(", ")}</p>
        </div>
      </motion.div>

      <motion.div
        className="flex items-center gap-4 rounded-xl bg-gray-50 p-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
          <Users className="h-5 w-5 text-purple-500" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Travel Styles</p>
          <p className="text-lg font-bold text-dark">{destination.travelStyles.join(", ")}</p>
        </div>
      </motion.div>

      <motion.div
        className="flex items-center gap-4 rounded-xl bg-gray-50 p-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
          <Heart className="h-5 w-5 text-red-400" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Popular Activities</p>
          <p className="text-base font-semibold text-dark">{destination.activities.slice(0, 4).map((a) => activityLabels[a]).join(" • ")}</p>
        </div>
      </motion.div>
    </motion.div>
  );
}
