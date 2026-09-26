"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Ticket, Wallet, Users2, AlertTriangle, ArrowRight } from "lucide-react";
import { loadBookings, seedGroups, loadChangeRequests, seedCoordinators } from "@/lib/operator-data";
import type { Booking, ItineraryChangeRequest } from "@/types/operator";
import StatusBadge from "@/components/operator/status-badge";
import { formatINR } from "@/lib/pricing";

export default function OperatorOverviewPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [changes, setChanges] = useState<ItineraryChangeRequest[]>([]);

  useEffect(() => {
    setBookings(loadBookings());
    setChanges(loadChangeRequests());
  }, []);

  const totalRevenue = bookings.reduce((sum, b) => sum + b.totalCost, 0);
  const activeTours = bookings.filter((b) => b.status === "confirmed" || b.status === "in-progress").length;
  const openChanges = changes.filter((c) => c.status === "open" || c.status === "reviewing").length;

  const kpis = [
    { label: "Total Bookings", value: bookings.length, icon: Ticket, tint: "bg-primary/10 text-primary" },
    { label: "Revenue", value: formatINR(totalRevenue), icon: Wallet, tint: "bg-emerald-100 text-emerald-600" },
    { label: "Active Tours", value: activeTours, icon: Users2, tint: "bg-blue-100 text-blue-600" },
    { label: "Open Itinerary Changes", value: openChanges, icon: AlertTriangle, tint: "bg-amber-100 text-amber-600" },
  ];

  return (
    <div className="mx-auto max-w-7xl">
      <h1 className="text-2xl font-bold text-dark">Operator Overview</h1>
      <p className="mt-1 text-sm text-gray-500">
        Visibility across customers, bookings, vendors, and coordinators — all in one place.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
              <span className={`flex h-10 w-10 items-center justify-center rounded-full ${kpi.tint}`}>
                <Icon className="h-5 w-5" />
              </span>
              <p className="mt-4 text-2xl font-bold text-dark">{kpi.value}</p>
              <p className="text-sm text-gray-500">{kpi.label}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-dark">Recent Bookings</h2>
            <Link href="/operator/bookings" className="text-sm font-semibold text-primary hover:text-primary/80">
              View All →
            </Link>
          </div>
          <div className="mt-4 divide-y divide-gray-50">
            {bookings.slice(0, 5).map((b) => (
              <Link
                key={b.id}
                href={`/operator/bookings/${b.id}`}
                className="flex items-center justify-between gap-3 py-3 text-sm hover:bg-gray-50"
              >
                <div>
                  <p className="font-semibold text-dark">{b.customerName}</p>
                  <p className="text-xs text-gray-500">
                    {b.destination} · {b.startDate}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-dark">{formatINR(b.totalCost)}</span>
                  <StatusBadge status={b.status} />
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-dark">Needs Attention</h2>
            <Link href="/operator/changes" className="text-sm font-semibold text-primary hover:text-primary/80">
              View All →
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {changes.slice(0, 3).map((c) => (
              <div key={c.id} className="rounded-2xl border border-amber-100 bg-amber-50 p-3">
                <p className="text-xs font-semibold text-dark">{c.reason}</p>
                <p className="mt-1 text-xs text-gray-600">{c.impact}</p>
                <div className="mt-2 flex items-center justify-between">
                  <StatusBadge status={c.status} />
                  <Link
                    href={`/operator/changes`}
                    className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                  >
                    Review <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            ))}
            {changes.length === 0 && <p className="text-sm text-gray-400">No open items. All clear.</p>}
          </div>

          <div className="mt-5 border-t border-gray-100 pt-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Coordinators on duty</p>
            <p className="mt-2 text-sm text-gray-600">{seedCoordinators.length} coordinators managing {seedGroups.length} active groups</p>
          </div>
        </div>
      </div>
    </div>
  );
}
