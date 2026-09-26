export type TripActivityType =
  | "sightseeing"
  | "food"
  | "adventure"
  | "relaxation"
  | "culture"
  | "shopping"
  | "transport"
  | "accommodation"
  | "custom";

export type TripActivity = {
  id: string;
  type: TripActivityType;
  title: string;
  description: string;
  time: string;
  duration: string;
  notes: string;
};

export type TripDay = {
  id: string;
  date: string;
  title: string;
  activities: TripActivity[];
};

export type TripStatus = "draft" | "planned" | "booked" | "upcoming" | "completed";

export type Trip = {
  id: string;
  name: string;
  destination: string;
  destinationSlug: string;
  startDate: string;
  endDate: string;
  budget: string;
  travelers: number;
  days: TripDay[];
  createdAt: string;
  status?: TripStatus;
  coverImage?: string;
};

// The four stages shown on a trip's progress stepper. "draft" trips (still being
// built in the planner) don't have a stepper position yet.
export const tripStatusSteps: Exclude<TripStatus, "draft">[] = ["planned", "booked", "upcoming", "completed"];

export const tripStatusLabels: Record<TripStatus, string> = {
  draft: "Draft",
  planned: "Planned",
  booked: "Booked",
  upcoming: "Upcoming",
  completed: "Completed",
};

export const tripStatusBadgeStyles: Record<TripStatus, string> = {
  draft: "bg-gray-100 text-gray-600",
  planned: "bg-blue-100 text-blue-700",
  booked: "bg-primary/10 text-primary",
  upcoming: "bg-secondary/10 text-secondary",
  completed: "bg-purple-100 text-purple-700",
};

export const emptyTripActivity = (id: string = ""): TripActivity => ({
  id,
  type: "custom",
  title: "",
  description: "",
  time: "09:00",
  duration: "1h",
  notes: "",
});

export const activityTypeLabels: Record<TripActivityType, string> = {
  sightseeing: "Sightseeing",
  food: "Food",
  adventure: "Adventure",
  relaxation: "Relaxation",
  culture: "Culture",
  shopping: "Shopping",
  transport: "Transport",
  accommodation: "Accommodation",
  custom: "Custom",
};

export const activityTypeEmojis: Record<TripActivityType, string> = {
  sightseeing: "🏛️",
  food: "🍴",
  adventure: "🧗",
  relaxation: "🧘",
  culture: "🎭",
  shopping: "🛍️",
  transport: "🚗",
  accommodation: "🏨",
  custom: "📝",
};

export const presetActivities: { type: TripActivityType; title: string; duration: string; description?: string }[] = [
  { type: "sightseeing", title: "Landmarks Tour", duration: "2h", description: "Visit famous landmarks and monuments" },
  { type: "sightseeing", title: "City Walking Tour", duration: "3h", description: "Explore the city on foot" },
  { type: "food", title: "Local Food Tour", duration: "2h", description: "Taste local cuisine and street food" },
  { type: "food", title: "Market Visit", duration: "1h", description: "Browse local markets for fresh produce" },
  { type: "adventure", title: "Hiking Trail", duration: "4h", description: "Explore nature trails and scenic hikes" },
  { type: "adventure", title: "Water Sports", duration: "2h", description: "Enjoy water activities like snorkeling or kayaking" },
  { type: "relaxation", title: "Spa Day", duration: "3h", description: "Relax at a local spa or wellness center" },
  { type: "relaxation", title: "Beach Time", duration: "3h", description: "Relax on the beach" },
  { type: "culture", title: "Museum Visit", duration: "2h", description: "Discover local art and history" },
  { type: "culture", title: "Temple/Shrine Visit", duration: "1.5h", description: "Explore religious and cultural sites" },
  { type: "shopping", title: "Shopping District", duration: "2h", description: "Browse local shops and boutiques" },
  { type: "transport", title: "Airport Transfer", duration: "1h", description: "Transportation to/from airport" },
];

export const STORAGE_KEY = "voyager_trips";
