import { Ticket } from "lucide-react";
import ComingSoon from "@/components/dashboard/coming-soon";

export default function BookingsPage() {
  return (
    <ComingSoon
      icon={Ticket}
      title="Bookings"
      description="Confirmed flights, hotels, and activities will show up here once the Price → Book stage is wired up to real vendors."
    />
  );
}
