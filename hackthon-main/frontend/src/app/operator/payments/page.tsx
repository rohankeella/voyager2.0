"use client";

import { useEffect, useState } from "react";
import { seedPayments, loadBookings } from "@/lib/operator-data";
import type { Booking } from "@/types/operator";
import StatusBadge from "@/components/operator/status-badge";
import { formatINR } from "@/lib/pricing";

export default function OperatorPaymentsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);

  useEffect(() => {
    setBookings(loadBookings());
  }, []);

  const totalCollected = seedPayments.filter((p) => p.status === "success").reduce((s, p) => s + p.amount, 0);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-bold text-dark">Payments</h1>
      <p className="mt-1 text-sm text-gray-500">
        <span className="font-semibold text-dark">{formatINR(totalCollected)}</span> collected across all bookings.
      </p>

      <div className="mt-6 overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">
              <th className="px-5 py-3">Booking</th>
              <th className="px-5 py-3">Customer</th>
              <th className="px-5 py-3">Amount</th>
              <th className="px-5 py-3">Method</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {seedPayments.map((p) => {
              const booking = bookings.find((b) => b.id === p.bookingId);
              return (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-5 py-4 font-mono text-xs text-gray-500">{p.bookingId}</td>
                  <td className="px-5 py-4 font-medium text-dark">{booking?.customerName ?? "—"}</td>
                  <td className="px-5 py-4 font-semibold text-dark">{formatINR(p.amount)}</td>
                  <td className="px-5 py-4 text-gray-600">{p.method}</td>
                  <td className="px-5 py-4">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-5 py-4 text-gray-500">{new Date(p.createdAt).toLocaleDateString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
