import type { OnboardingData } from "@/types/onboarding";
import type { Destination, BudgetLevel, TripDuration, Season, Activity, DestinationType, Priority } from "@/lib/mock-data";
import { destinations } from "@/lib/mock-data";
import { recommendationsApi, type MatchRequest, type MatchResponse } from "@/lib/api";

const BUDGET_RANK: Record<BudgetLevel, number> = {
  backpacker: 1,
  budget: 2,
  comfortable: 3,
  premium: 4,
  luxury: 5,
};

export function calculateMatchScore(destination: Destination, preferences: OnboardingData): number {
  if (!preferences.travelerTypes.length && !preferences.activities.length && !preferences.destinationTypes.length) {
    return Math.floor(Math.random() * (98 - 75) + 75);
  }

  let score = 0;
  let maxScore = 0;

  if (preferences.activities.length > 0) {
    maxScore += 30;
    const activityMatches = preferences.activities.filter((a) => destination.activities.includes(a)).length;
    score += Math.round((activityMatches / preferences.activities.length) * 30);
  }

  if (preferences.travelerTypes.length > 0) {
    maxScore += 15;
    const styleMatch = destination.travelStyles.some((style) =>
      preferences.travelerTypes.some((t) => style.includes(t.replace("-seeker", "").replace("-lover", "").replace("-explorer", "")))
    );
    if (styleMatch) score += 15;
  }

  if (preferences.destinationTypes.length > 0) {
    maxScore += 20;
    const destinationMatches = preferences.destinationTypes.filter((d) =>
      destination.destinationTypes.includes(d)
    ).length;
    score += Math.round((destinationMatches / preferences.destinationTypes.length) * 20);
  }

  if (preferences.budget) {
    maxScore += 15;
    const userBudgetRank = BUDGET_RANK[preferences.budget as BudgetLevel] || 3;
    const destBudgetRank = BUDGET_RANK[destination.budget] || 3;
    const diff = Math.abs(userBudgetRank - destBudgetRank);
    if (diff === 0) score += 15;
    else if (diff === 1) score += 10;
    else if (diff === 2) score += 5;
  }

  if (preferences.duration) {
    maxScore += 10;
    if (destination.recommendedDuration.includes(preferences.duration as TripDuration)) {
      score += 10;
    }
  }

  if (preferences.seasons.length > 0) {
    maxScore += 10;
    const seasonMatches = preferences.seasons.filter((s) => destination.bestSeason.includes(s)).length;
    score += Math.round((seasonMatches / preferences.seasons.length) * 10);
  }

  if (preferences.travelPace) {
    maxScore += 10;
    if (
      (preferences.travelPace === "slow-relaxed" && (destination.budget === "premium" || destination.budget === "luxury")) ||
      (preferences.travelPace === "adventure-packed" && destination.activities.some((a) => ["hiking", "trekking", "camping", "skiing"].includes(a))) ||
      (preferences.travelPace === "packed-schedule" && destination.activities.length >= 5)
    ) {
      score += 10;
    } else if (preferences.travelPace === "balanced") {
      score += 7;
    }
  }

  if (preferences.priorities.length > 0) {
    maxScore += 10;
    const topPriority = preferences.priorities[0] as Priority;
    if (topPriority === "price" && destination.estimatedDailyCost < 100) score += 10;
    else if (topPriority === "food" && destination.activities.includes("food-tours")) score += 10;
    else if (topPriority === "nature" && destination.destinationTypes.some((d) => ["mountains", "forests", "countryside"].includes(d))) score += 10;
    else if (topPriority === "adventure" && destination.activities.some((a) => ["hiking", "trekking", "skiing", "camping"].includes(a))) score += 10;
    else if (topPriority === "luxury" && destination.budget === "luxury") score += 10;
    else score += 5;
  }

  const finalScore = maxScore > 0 ? Math.round((score / maxScore) * 100) : 75;
  return Math.min(99, Math.max(65, finalScore));
}

export function getTopDestinations(preferences: OnboardingData, count = 8): Destination[] {
  const scored = destinations.map((d) => ({
    ...d,
    matchScore: calculateMatchScore(d, preferences),
  }));

  return scored.sort((a, b) => (b.matchScore ?? 0) - (a.matchScore ?? 0)).slice(0, count);
}

export function getDestinationBySlug(slug: string): Destination | undefined {
  return destinations.find((d) => d.slug === slug);
}

// ---- Live backend-powered experience recommendations ----------------------
// The functions above rank *destinations* using local mock data. The
// backend Multi-Factor Matching Engine (F-01) ranks individual
// *experiences* (activities, restaurants, workshops, tours) for a specific
// location + free window. Both coexist: destinations for planning, live
// experiences for on-trip discovery + gap-filling.

const BUDGET_TO_DAILY_MAX_INR: Record<BudgetLevel, number> = {
  backpacker: 2500,
  budget: 5000,
  comfortable: 10000,
  premium: 20000,
  luxury: 40000,
};

export function buildMatchRequestFromPreferences(
  preferences: OnboardingData,
  location: { lat: number; lng: number; city?: string },
  window: { at: Date; windowEnd: Date },
  overrides: Partial<MatchRequest> = {},
): MatchRequest {
  const dailyMax =
    typeof preferences.customDailyBudget === "number" && preferences.customDailyBudget > 0
      ? preferences.customDailyBudget
      : preferences.budget
      ? BUDGET_TO_DAILY_MAX_INR[preferences.budget as BudgetLevel]
      : null;

  return {
    lat: location.lat,
    lng: location.lng,
    at: window.at.toISOString(),
    window_end: window.windowEnd.toISOString(),
    interests: preferences.activities,
    priorities: preferences.priorities,
    budget_max: dailyMax,
    group_type: preferences.tripStyle || null,
    travel_mode: "driving",
    limit: 20,
    city: location.city,
    ...overrides,
  };
}

export async function fetchExperienceMatches(
  preferences: OnboardingData,
  location: { lat: number; lng: number; city?: string },
  window: { at: Date; windowEnd: Date },
): Promise<MatchResponse> {
  const req = buildMatchRequestFromPreferences(preferences, location, window);
  return recommendationsApi.match(req);
}
