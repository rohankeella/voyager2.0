export type BookingStatus = "pending" | "confirmed" | "in-progress" | "completed" | "cancelled";
export type PaymentStatus = "unpaid" | "partial" | "paid" | "refunded";

export type CostBreakdownItem = { label: string; amount: number };

export type Booking = {
  id: string;
  tripId?: string;
  customerName: string;
  customerEmail: string;
  destination: string;
  startDate: string;
  endDate: string;
  travelers: number;
  costBreakdown: CostBreakdownItem[];
  totalCost: number;
  status: BookingStatus;
  paymentStatus: PaymentStatus;
  coordinatorId?: string;
  groupId?: string;
  createdAt: string;
};

export type VendorType = "hotel" | "transport" | "activity";

export type Vendor = {
  id: string;
  name: string;
  type: VendorType;
  location: string;
  rating: number;
  contact: string;
  pricePerUnit: number;
  unitLabel: string;
  status: "active" | "inactive";
};

export type Coordinator = {
  id: string;
  name: string;
  email: string;
  phone: string;
  region: string;
};

export type TourGroupStatus = "forming" | "confirmed" | "in-progress" | "completed";

export type TourGroup = {
  id: string;
  name: string;
  destination: string;
  startDate: string;
  endDate: string;
  bookingIds: string[];
  coordinatorId: string;
  status: TourGroupStatus;
};

export type ChangeRequestStatus = "open" | "reviewing" | "resolved" | "rejected";

export type ItineraryChangeRequest = {
  id: string;
  bookingId: string;
  raisedBy: "traveler" | "operator" | "system";
  reason: string;
  impact: string;
  suggestedResolution: string;
  status: ChangeRequestStatus;
  createdAt: string;
};

export type PaymentRecord = {
  id: string;
  bookingId: string;
  amount: number;
  method: string;
  status: "success" | "pending" | "failed" | "refunded";
  createdAt: string;
};

export const BOOKINGS_STORAGE_KEY = "voyager_bookings";
