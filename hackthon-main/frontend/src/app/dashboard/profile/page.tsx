import { User } from "lucide-react";
import ComingSoon from "@/components/dashboard/coming-soon";

export default function ProfilePage() {
  return (
    <ComingSoon
      icon={User}
      title="Profile"
      description="Manage your traveler profile, preferences, and travel history."
    />
  );
}
