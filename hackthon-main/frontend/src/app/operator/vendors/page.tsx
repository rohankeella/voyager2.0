"use client";

import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import { loadVendors, updateVendorStatus } from "@/lib/operator-data";
import type { Vendor, VendorType } from "@/types/operator";
import StatusBadge from "@/components/operator/status-badge";
import { cn } from "@/lib/utils";

const tabs: { label: string; value: VendorType | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Hotels", value: "hotel" },
  { label: "Transport", value: "transport" },
  { label: "Activities", value: "activity" },
];

export default function OperatorVendorsPage() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [tab, setTab] = useState<VendorType | "all">("all");

  useEffect(() => {
    setVendors(loadVendors());
  }, []);

  const filtered = tab === "all" ? vendors : vendors.filter((v) => v.type === tab);

  const toggleStatus = (v: Vendor) => {
    const next = v.status === "active" ? "inactive" : "active";
    setVendors(updateVendorStatus(v.id, next));
  };

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-bold text-dark">Vendors & Hotels</h1>
      <p className="mt-1 text-sm text-gray-500">Hotels, transportation, and activity providers in your network.</p>

      <div className="mt-6 flex gap-2 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={cn(
              "shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition-colors",
              tab === t.value ? "bg-dark text-white" : "bg-white text-gray-600 hover:bg-gray-50"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {filtered.map((v) => (
          <div key={v.id} className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-dark">{v.name}</p>
                <p className="text-xs capitalize text-gray-500">
                  {v.type} · {v.location}
                </p>
              </div>
              <StatusBadge status={v.status} />
            </div>
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="flex items-center gap-1 text-gray-500">
                <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" /> {v.rating}
              </span>
              <span className="font-medium text-dark">
                ₹{v.pricePerUnit.toLocaleString("en-IN")} <span className="text-xs text-gray-400">{v.unitLabel}</span>
              </span>
            </div>
            <p className="mt-2 text-xs text-gray-400">{v.contact}</p>
            <button
              onClick={() => toggleStatus(v)}
              className="mt-3 w-full rounded-full border border-gray-200 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50"
            >
              Mark as {v.status === "active" ? "Inactive" : "Active"}
            </button>
          </div>
        ))}
        {filtered.length === 0 && <p className="text-sm text-gray-400">No vendors in this category.</p>}
      </div>
    </div>
  );
}
