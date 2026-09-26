"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Ticket,
  Users,
  Building2,
  UserCog,
  Users2,
  Wallet,
  AlertTriangle,
  Compass,
} from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/operator/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/operator/bookings", label: "Bookings", icon: Ticket },
  { href: "/operator/customers", label: "Customers", icon: Users },
  { href: "/operator/vendors", label: "Vendors & Hotels", icon: Building2 },
  { href: "/operator/groups", label: "Tour Groups", icon: Users2 },
  { href: "/operator/coordinators", label: "Coordinators", icon: UserCog },
  { href: "/operator/payments", label: "Payments", icon: Wallet },
  { href: "/operator/changes", label: "Itinerary Changes", icon: AlertTriangle },
];

export default function OperatorSidebar() {
  const pathname = usePathname();
  const isActive = (href: string) => pathname === href || pathname?.startsWith(href);

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-gray-100 bg-white lg:flex">
      <div className="flex h-16 items-center gap-2 border-b border-gray-100 px-6">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-dark to-dark/70 text-white">
          <Compass className="h-4 w-4" />
        </span>
        <div className="leading-tight">
          <p className="text-lg font-bold tracking-tight text-dark">Voyager</p>
          <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400">Operator Console</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {links.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                active ? "bg-dark text-white" : "text-gray-600 hover:bg-gray-50 hover:text-dark"
              )}
            >
              <Icon className="h-[18px] w-[18px]" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="m-3 rounded-2xl border border-gray-100 bg-gray-50 p-4 text-xs text-gray-500">
        <p className="font-semibold text-dark">Traveler view</p>
        <p className="mt-1">
          Switch to the{" "}
          <Link href="/dashboard/home" className="font-semibold text-primary hover:underline">
            traveler dashboard
          </Link>{" "}
          to see the customer-facing side.
        </p>
      </div>
    </aside>
  );
}
