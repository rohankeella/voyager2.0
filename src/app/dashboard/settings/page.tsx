import { Settings } from "lucide-react";
import ComingSoon from "@/components/dashboard/coming-soon";

export default function SettingsPage() {
  return (
    <ComingSoon
      icon={Settings}
      title="Settings"
      description="Account, notification, and privacy settings."
    />
  );
}
