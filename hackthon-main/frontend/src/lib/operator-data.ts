import type {
  Booking,
  ChangeRequestStatus,
  Coordinator,
  ItineraryChangeRequest,
  PaymentRecord,
  TourGroup,
  Vendor,
} from "@/types/operator";

export const seedVendors: Vendor[] = [
  {
    id: "v1",
    name: "Coral Reef Resort",
    type: "hotel",
    location: "Goa, India",
    rating: 4.5,
    contact: "bookings@coralreefgoa.com",
    pricePerUnit: 6500,
    unitLabel: "per night",
    status: "active",
  },
  {
    id: "v2",
    name: "Snow Valley Resorts",
    type: "hotel",
    location: "Manali, India",
    rating: 4.3,
    contact: "reservations@snowvalley.in",
    pricePerUnit: 4200,
    unitLabel: "per night",
    status: "active",
  },
  {
    id: "v3",
    name: "BlueWave Transfers",
    type: "transport",
    location: "Goa, India",
    rating: 4.1,
    contact: "ops@bluewavetransfers.com",
    pricePerUnit: 1800,
    unitLabel: "per transfer",
    status: "active",
  },
  {
    id: "v4",
    name: "Himalayan Road Trips",
    type: "transport",
    location: "Manali, India",
    rating: 4.6,
    contact: "dispatch@himalayanroadtrips.com",
    pricePerUnit: 3200,
    unitLabel: "per day",
    status: "active",
  },
  {
    id: "v5",
    name: "Spice Route Cooking Class",
    type: "activity",
    location: "Goa, India",
    rating: 4.8,
    contact: "hello@spiceroutegoa.com",
    pricePerUnit: 1200,
    unitLabel: "per person",
    status: "active",
  },
  {
    id: "v6",
    name: "Meghalaya Trek Guides",
    type: "activity",
    location: "Meghalaya, India",
    rating: 4.7,
    contact: "book@meghalayatrek.com",
    pricePerUnit: 2500,
    unitLabel: "per person",
    status: "inactive",
  },
];

export const seedCoordinators: Coordinator[] = [
  { id: "c1", name: "Ananya Rao", email: "ananya@voyager.travel", phone: "+91 98200 11223", region: "West India" },
  { id: "c2", name: "Vikram Shah", email: "vikram@voyager.travel", phone: "+91 98700 44556", region: "North India" },
  { id: "c3", name: "Priya Menon", email: "priya@voyager.travel", phone: "+91 97400 77889", region: "North-East India" },
];

export const seedBookings: Booking[] = [
  {
    id: "bk-1001",
    customerName: "Rohan Kapoor",
    customerEmail: "rohan.kapoor@example.com",
    destination: "Goa",
    startDate: "2026-11-12",
    endDate: "2026-11-16",
    travelers: 2,
    costBreakdown: [
      { label: "Accommodation", amount: 18500 },
      { label: "Activities & Experiences", amount: 9200 },
      { label: "Food & Dining", amount: 7400 },
      { label: "Transport & Transfers", amount: 6900 },
      { label: "Service Fee", amount: 2100 },
    ],
    totalCost: 44100,
    status: "confirmed",
    paymentStatus: "paid",
    coordinatorId: "c1",
    groupId: "g1",
    createdAt: "2026-09-02T10:00:00.000Z",
  },
  {
    id: "bk-1002",
    customerName: "Sanya Verma",
    customerEmail: "sanya.verma@example.com",
    destination: "Manali",
    startDate: "2027-01-05",
    endDate: "2027-01-12",
    travelers: 4,
    costBreakdown: [
      { label: "Accommodation", amount: 29400 },
      { label: "Activities & Experiences", amount: 15300 },
      { label: "Food & Dining", amount: 12200 },
      { label: "Transport & Transfers", amount: 16800 },
      { label: "Service Fee", amount: 3700 },
    ],
    totalCost: 77400,
    status: "pending",
    paymentStatus: "partial",
    coordinatorId: "c2",
    groupId: "g2",
    createdAt: "2026-09-10T14:30:00.000Z",
  },
  {
    id: "bk-1003",
    customerName: "Arjun Nair",
    customerEmail: "arjun.nair@example.com",
    destination: "Kashmir",
    startDate: "2026-04-10",
    endDate: "2026-04-15",
    travelers: 2,
    costBreakdown: [
      { label: "Accommodation", amount: 22000 },
      { label: "Activities & Experiences", amount: 11500 },
      { label: "Food & Dining", amount: 8300 },
      { label: "Transport & Transfers", amount: 9200 },
      { label: "Service Fee", amount: 2550 },
    ],
    totalCost: 53550,
    status: "completed",
    paymentStatus: "paid",
    coordinatorId: "c3",
    createdAt: "2026-03-01T09:15:00.000Z",
  },
];

export const seedGroups: TourGroup[] = [
  {
    id: "g1",
    name: "Goa Coastal Getaway — Nov Batch",
    destination: "Goa",
    startDate: "2026-11-12",
    endDate: "2026-11-16",
    bookingIds: ["bk-1001"],
    coordinatorId: "c1",
    status: "confirmed",
  },
  {
    id: "g2",
    name: "Manali Adventure — Jan Batch",
    destination: "Manali",
    startDate: "2027-01-05",
    endDate: "2027-01-12",
    bookingIds: ["bk-1002"],
    coordinatorId: "c2",
    status: "forming",
  },
];

export const seedPayments: PaymentRecord[] = [
  { id: "py-1", bookingId: "bk-1001", amount: 44100, method: "UPI", status: "success", createdAt: "2026-09-02T10:05:00.000Z" },
  { id: "py-2", bookingId: "bk-1002", amount: 30000, method: "Credit Card", status: "success", createdAt: "2026-09-10T14:35:00.000Z" },
  { id: "py-3", bookingId: "bk-1002", amount: 47400, method: "Credit Card", status: "pending", createdAt: "2026-09-20T11:00:00.000Z" },
  { id: "py-4", bookingId: "bk-1003", amount: 53550, method: "Net Banking", status: "success", createdAt: "2026-03-01T09:20:00.000Z" },
];

export const seedChangeRequests: ItineraryChangeRequest[] = [
  {
    id: "cr-1",
    bookingId: "bk-1001",
    raisedBy: "system",
    reason: "Heavy rain forecast in Goa for Nov 13",
    impact: "Outdoor water-sports activity on Day 2 is at risk of cancellation.",
    suggestedResolution: "Swap water-sports slot for the Spice Route Cooking Class and move it earlier in the day.",
    status: "open",
    createdAt: "2026-09-19T08:00:00.000Z",
  },
  {
    id: "cr-2",
    bookingId: "bk-1002",
    raisedBy: "traveler",
    reason: "Customer requested an extra night in Manali",
    impact: "Adds 1 night of accommodation and shifts the return transfer by a day; +₹4,200 estimated.",
    suggestedResolution: "Confirm availability with Snow Valley Resorts and re-quote the customer before extending.",
    status: "reviewing",
    createdAt: "2026-09-15T12:00:00.000Z",
  },
];

function readJSON<T>(key: string): T[] | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

const BOOKINGS_KEY = "voyager_bookings";
const VENDORS_KEY = "voyager_vendors";
const CHANGE_REQUESTS_KEY = "voyager_change_requests";

export function loadBookings(): Booking[] {
  const stored = readJSON<Booking>(BOOKINGS_KEY);
  if (stored && stored.length > 0) {
    // Real bookings created through /booking take priority, demo data fills in behind them.
    const storedIds = new Set(stored.map((b) => b.id));
    return [...stored, ...seedBookings.filter((b) => !storedIds.has(b.id))];
  }
  return seedBookings;
}

// Persists a status/payment change back to localStorage. The first edit an
// operator makes "promotes" the merged seed+real dataset into storage, so
// further loads reflect it.
export function updateBooking(id: string, patch: Partial<Booking>): Booking[] {
  const current = loadBookings().map((b) => (b.id === id ? { ...b, ...patch } : b));
  try {
    localStorage.setItem(BOOKINGS_KEY, JSON.stringify(current));
  } catch {
    // ignore
  }
  return current;
}

export function loadVendors(): Vendor[] {
  const stored = readJSON<Vendor>(VENDORS_KEY);
  if (stored && stored.length > 0) return stored;
  return seedVendors;
}

export function updateVendorStatus(id: string, status: Vendor["status"]): Vendor[] {
  const current = loadVendors().map((v) => (v.id === id ? { ...v, status } : v));
  try {
    localStorage.setItem(VENDORS_KEY, JSON.stringify(current));
  } catch {
    // ignore
  }
  return current;
}

export function loadChangeRequests(): ItineraryChangeRequest[] {
  const stored = readJSON<ItineraryChangeRequest>(CHANGE_REQUESTS_KEY);
  if (stored && stored.length > 0) return stored;
  return seedChangeRequests;
}

export function updateChangeRequestStatus(id: string, status: ChangeRequestStatus): ItineraryChangeRequest[] {
  const current = loadChangeRequests().map((c) => (c.id === id ? { ...c, status } : c));
  try {
    localStorage.setItem(CHANGE_REQUESTS_KEY, JSON.stringify(current));
  } catch {
    // ignore
  }
  return current;
}
