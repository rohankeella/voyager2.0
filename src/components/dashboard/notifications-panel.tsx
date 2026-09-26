import Link from "next/link";
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

export default function NotificationsPanel() {
  return (
    <div className="rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-dark">Notifications</h3>
        <Link href="/dashboard/notifications" className="text-xs font-semibold text-primary hover:text-primary/80">
          View All
        </Link>
      </div>

      <div className="mt-4 space-y-2">
        {notifications.map((n) => {
          const Icon = toneIcon[n.tone];
          return (
            <div key={n.id} className={cn("flex gap-3 rounded-2xl border p-3", toneStyles[n.tone])}>
              <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", toneIconColor[n.tone])} />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-dark">{n.title}</p>
                <p className="mt-0.5 line-clamp-2 text-xs text-gray-600">{n.description}</p>
                <p className="mt-1 text-[10px] text-gray-400">{n.timeAgo}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
