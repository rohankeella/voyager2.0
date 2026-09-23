import type { Trip } from "@/types/trip";

// Seed trips shown the first time a visitor lands on the dashboard, before they've
// created anything of their own in the planner. Once a real trip exists in
// localStorage (voyager_trips), that takes over.
export const seedTrips: Trip[] = [
  {
    id: "seed-goa",
    name: "Goa Getaway",
    destination: "Goa",
    destinationSlug: "goa",
    startDate: "2026-11-12",
    endDate: "2026-11-16",
    budget: "comfortable",
    travelers: 2,
    days: [],
    createdAt: new Date().toISOString(),
    status: "upcoming",
    coverImage:
      "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1200&q=80",
  },
  {
    id: "seed-meghalaya",
    name: "Meghalaya Adventure",
    destination: "Meghalaya",
    destinationSlug: "meghalaya",
    startDate: "2027-01-05",
    endDate: "2027-01-12",
    budget: "budget",
    travelers: 4,
    days: [],
    createdAt: new Date().toISOString(),
    status: "draft",
    coverImage:
      "https://images.unsplash.com/photo-1544644181-1484b3fdfc62?auto=format&fit=crop&w=1200&q=80",
  },
  {
    id: "seed-kashmir",
    name: "Kashmir Escape",
    destination: "Kashmir",
    destinationSlug: "kashmir",
    startDate: "2026-04-10",
    endDate: "2026-04-15",
    budget: "premium",
    travelers: 2,
    days: [],
    createdAt: new Date().toISOString(),
    status: "completed",
    coverImage:
      "https://images.unsplash.com/photo-1566837945700-30057527ade0?auto=format&fit=crop&w=1200&q=80",
  },
];

export type DashboardNotification = {
  id: string;
  tone: "alert" | "info" | "success";
  title: string;
  description: string;
  timeAgo: string;
};

export const notifications: DashboardNotification[] = [
  {
    id: "n1",
    tone: "alert",
    title: "Heavy rain expected in Goa",
    description: "Tomorrow's plan may be affected — we've suggested alternative indoor activities.",
    timeAgo: "2h ago",
  },
  {
    id: "n2",
    tone: "success",
    title: "Your flight to Goa is confirmed",
    description: "IndiGo 6E-204, 12 Nov, 09:40 from BOM.",
    timeAgo: "5h ago",
  },
  {
    id: "n3",
    tone: "info",
    title: "Hotel check-in details are available",
    description: "Coral Reef Resort — check-in from 2:00 PM.",
    timeAgo: "1d ago",
  },
];

export const aiSuggestedPrompts: string[] = [
  "Plan a 5 day trip to Bali under ₹50,000",
  "Find family-friendly hotels in Manali",
  "What can I do if my flight is delayed?",
  "Suggest indoor activities for a rainy day",
  "Optimize my current itinerary",
];
