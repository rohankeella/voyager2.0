import { CloudRain, PlaneTakeoff, BedDouble } from "lucide-react";
import { notifications, type DashboardNotification } from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";

const toneStyles: Record<DashboardNotification["tone"], string> = {
  alert: "bg-red-50 border-red-100",
  info: "bg-blue-50 border-blue-100",
  success: "bg-emerald-50 border-emerald-100",
};

const toneIcon: Record<DashboardNotification["tone"], typeof CloudRain> = {
  alert: CloudRain,
  info: BedDouble,
  success: PlaneTakeoff,
};

const toneIconColor: Record<DashboardNotification["tone"], string> = {
  alert: "text-red-500",
  info: "text-blue-500",
  success: "text-emerald-500",
};

export default function NotificationsPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-dark">Notifications</h1>
      <p className="mt-1 text-sm text-gray-500">Updates on your trips, bookings, and disruptions.</p>

      <div className="mt-6 space-y-3">
        {notifications.map((n) => {
          const Icon = toneIcon[n.tone];
          return (
            <div key={n.id} className={cn("flex gap-3 rounded-2xl border p-4", toneStyles[n.tone])}>
              <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", toneIconColor[n.tone])} />
              <div>
                <p className="text-sm font-semibold text-dark">{n.title}</p>
                <p className="mt-0.5 text-sm text-gray-600">{n.description}</p>
                <p className="mt-1 text-xs text-gray-400">{n.timeAgo}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
