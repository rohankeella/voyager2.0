"use client";

import { useEffect, useState } from "react";
import { loadBookings } from "@/lib/operator-data";
import type { Booking } from "@/types/operator";
import { formatINR } from "@/lib/pricing";

type CustomerRow = {
  name: string;
  email: string;
  trips: number;
  totalSpend: number;
  lastDestination: string;
};

function toCustomers(bookings: Booking[]): CustomerRow[] {
  const map = new Map<string, CustomerRow>();
  for (const b of bookings) {
    const existing = map.get(b.customerEmail);
    if (existing) {
      existing.trips += 1;
      existing.totalSpend += b.totalCost;
      existing.lastDestination = b.destination;
    } else {
      map.set(b.customerEmail, {
        name: b.customerName,
        email: b.customerEmail,
        trips: 1,
        totalSpend: b.totalCost,
        lastDestination: b.destination,
      });
    }
  }
  return Array.from(map.values());
}

export default function OperatorCustomersPage() {
  const [customers, setCustomers] = useState<CustomerRow[]>([]);

  useEffect(() => {
    setCustomers(toCustomers(loadBookings()));
  }, []);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-bold text-dark">Customers</h1>
      <p className="mt-1 text-sm text-gray-500">Derived from booking activity across the platform.</p>

      <div className="mt-6 overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">
              <th className="px-5 py-3">Name</th>
              <th className="px-5 py-3">Email</th>
              <th className="px-5 py-3">Trips</th>
              <th className="px-5 py-3">Total Spend</th>
              <th className="px-5 py-3">Last Destination</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {customers.map((c) => (
              <tr key={c.email} className="hover:bg-gray-50">
                <td className="px-5 py-4 font-semibold text-dark">{c.name}</td>
                <td className="px-5 py-4 text-gray-500">{c.email}</td>
                <td className="px-5 py-4 text-gray-600">{c.trips}</td>
                <td className="px-5 py-4 font-medium text-dark">{formatINR(c.totalSpend)}</td>
                <td className="px-5 py-4 text-gray-600">{c.lastDestination}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {customers.length === 0 && <p className="p-10 text-center text-sm text-gray-400">No customers yet.</p>}
      </div>
    </div>
  );
}
