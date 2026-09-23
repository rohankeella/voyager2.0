"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PlusCircle,
  Map,
  Compass,
  Ticket,
  Heart,
  Bell,
  Sparkles,
  User,
  CreditCard,
  Settings,
  Plane,
} from "lucide-react";
import { cn } from "@/lib/utils";

const mainLinks = [
  { href: "/dashboard/home", label: "Dashboard", icon: LayoutDashboard },
  { href: "/onboarding", label: "Create New Trip", icon: PlusCircle },
  { href: "/dashboard/trips", label: "My Trips", icon: Map },
  { href: "/discover", label: "Explore Destinations", icon: Compass },
  { href: "/dashboard/bookings", label: "Bookings", icon: Ticket },
  { href: "/dashboard/saved", label: "Saved Places", icon: Heart },
  { href: "/dashboard/notifications", label: "Notifications", icon: Bell, badge: 3 },
  { href: "/dashboard/assistant", label: "AI Assistant", icon: Sparkles },
];

const accountLinks = [
  { href: "/dashboard/profile", label: "Profile", icon: User },
  { href: "/dashboard/payment-methods", label: "Payment Methods", icon: CreditCard },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => pathname === href || (href !== "/dashboard/home" && pathname?.startsWith(href));

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-gray-100 bg-white lg:flex">
      <div className="flex h-16 items-center gap-2 border-b border-gray-100 px-6">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary text-white">
          <Plane className="h-4 w-4" />
        </span>
        <div className="leading-tight">
          <p className="text-lg font-bold tracking-tight text-dark">Voyager</p>
          <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400">
            Plan · Adapt · Explore
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {mainLinks.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.href);
          return (
            <Link
              key={link.label}
              href={link.href}
              className={cn(
                "flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                active ? "bg-primary/10 text-primary" : "text-gray-600 hover:bg-gray-50 hover:text-dark"
              )}
            >
              <span className="flex items-center gap-3">
                <Icon className="h-[18px] w-[18px]" />
                {link.label}
              </span>
              {link.badge ? (
                <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[11px] font-semibold text-white">
                  {link.badge}
                </span>
              ) : null}
            </Link>
          );
        })}

        <div className="my-3 border-t border-gray-100" />

        {accountLinks.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.href);
          return (
            <Link
              key={link.label}
              href={link.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                active ? "bg-primary/10 text-primary" : "text-gray-600 hover:bg-gray-50 hover:text-dark"
              )}
            >
              <Icon className="h-[18px] w-[18px]" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="m-3 overflow-hidden rounded-2xl bg-gradient-to-br from-dark to-dark/80 p-5 text-white">
        <p className="text-base font-bold leading-snug">Explore More, Worry Less</p>
        <p className="mt-1.5 text-xs text-white/70">
          Let AI handle the details — you enjoy the journey.
        </p>
        <Link
          href="/onboarding"
          className="mt-4 inline-flex w-full items-center justify-center rounded-full bg-white px-4 py-2 text-xs font-semibold text-dark transition-colors hover:bg-white/90"
        >
          Plan Your Next Trip →
        </Link>
      </div>
    </aside>
  );
}
