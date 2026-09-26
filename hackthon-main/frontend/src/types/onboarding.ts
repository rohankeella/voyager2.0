export type TravelerType =
  | "adventure-seeker"
  | "relaxation-lover"
  | "culture-explorer"
  | "foodie"
  | "nature-lover"
  | "luxury-traveler"
  | "budget-traveler"
  | "digital-nomad";

export type TripStyle = "solo" | "couple" | "friends" | "family" | "group" | "business-leisure";

export type Activity =
  | "hiking"
  | "beaches"
  | "trekking"
  | "scuba-diving"
  | "skiing"
  | "museums"
  | "historical-places"
  | "nightlife"
  | "shopping"
  | "food-tours"
  | "photography"
  | "wildlife"
  | "camping"
  | "road-trips"
  | "water-sports"
  | "festivals";

export type DestinationType =
  | "beaches"
  | "mountains"
  | "cities"
  | "countryside"
  | "islands"
  | "forests"
  | "deserts"
  | "historical-cities"
  | "tropical"
  | "snow";

export type BudgetLevel = "backpacker" | "budget" | "comfortable" | "premium" | "luxury";

export type TripDuration = "weekend" | "3-5-days" | "1-week" | "1-2-weeks" | "2-4-weeks" | "1-month-plus";

export type Season = "spring" | "summer" | "monsoon" | "autumn" | "winter";

export type TravelPace = "slow-relaxed" | "balanced" | "packed-schedule" | "adventure-packed";

export type Priority =
  | "price"
  | "weather"
  | "food"
  | "safety"
  | "nature"
  | "culture"
  | "nightlife"
  | "adventure"
  | "luxury"
  | "accessibility";

export type OnboardingData = {
  travelerTypes: TravelerType[];
  tripStyle: TripStyle | "";
  activities: Activity[];
  destinationTypes: DestinationType[];
  budget: BudgetLevel | "";
  customDailyBudget: number | "";
  duration: TripDuration | "";
  seasons: Season[];
  travelPace: TravelPace | "";
  priorities: Priority[];
  additionalNotes: string;
};

export const emptyOnboardingData: OnboardingData = {
  travelerTypes: [],
  tripStyle: "",
  activities: [],
  destinationTypes: [],
  budget: "",
  customDailyBudget: "",
  duration: "",
  seasons: [],
  travelPace: "",
  priorities: [],
  additionalNotes: "",
};
