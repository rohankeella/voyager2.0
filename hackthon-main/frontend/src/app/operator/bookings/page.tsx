"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { loadBookings } from "@/lib/operator-data";
import type { Booking } from "@/types/operator";
import StatusBadge from "@/components/operator/status-badge";
import { formatINR } from "@/lib/pricing";

export default function OperatorBookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);

  useEffect(() => {
    setBookings(loadBookings());
  }, []);

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-2xl font-bold text-dark">Bookings</h1>
      <p className="mt-1 text-sm text-gray-500">Every customized tour booked through the platform.</p>

      <div className="mt-6 overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">Destination</th>
                <th className="px-5 py-3">Dates</th>
                <th className="px-5 py-3">Travelers</th>
                <th className="px-5 py-3">Total</th>
                <th className="px-5 py-3">Payment</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {bookings.map((b) => (
                <tr key={b.id} className="cursor-pointer hover:bg-gray-50">
                  <td className="px-5 py-4">
                    <Link href={`/operator/bookings/${b.id}`} className="block">
                      <p className="font-semibold text-dark">{b.customerName}</p>
                      <p className="text-xs text-gray-400">{b.id}</p>
                    </Link>
                  </td>
                  <td className="px-5 py-4 text-gray-600">{b.destination}</td>
                  <td className="px-5 py-4 text-gray-600">
                    {b.startDate} – {b.endDate}
                  </td>
                  <td className="px-5 py-4 text-gray-600">{b.travelers}</td>
                  <td className="px-5 py-4 font-semibold text-dark">{formatINR(b.totalCost)}</td>
                  <td className="px-5 py-4">
                    <StatusBadge status={b.paymentStatus} />
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={b.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {bookings.length === 0 && <p className="p-10 text-center text-sm text-gray-400">No bookings yet.</p>}
      </div>
    </div>
  );
}
