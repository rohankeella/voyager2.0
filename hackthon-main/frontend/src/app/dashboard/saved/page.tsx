import { Heart } from "lucide-react";
import ComingSoon from "@/components/dashboard/coming-soon";

export default function SavedPlacesPage() {
  return (
    <ComingSoon
      icon={Heart}
      title="Saved Places"
      description="Destinations and experiences you favorite from Discover will be collected here."
    />
  );
}
