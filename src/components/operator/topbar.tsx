"use client";

import { Search } from "lucide-react";

export default function OperatorTopbar({ userName = "Priya" }: { userName?: string }) {
  const initials = userName.slice(0, 2).toUpperCase();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-gray-100 bg-white/90 px-4 backdrop-blur-sm sm:px-6">
      <div className="relative hidden flex-1 max-w-md sm:block">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          placeholder="Search bookings, customers, vendors..."
          className="w-full rounded-full border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-4 text-sm text-dark placeholder:text-gray-400 focus:border-dark focus:bg-white focus:outline-none focus:ring-2 focus:ring-dark/10"
        />
      </div>

      <div className="ml-auto flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-dark/10 text-sm font-semibold text-dark">
          {initials}
        </span>
        <span className="hidden text-left sm:block">
          <span className="block text-sm font-semibold leading-tight text-dark">Hi, {userName}</span>
          <span className="block text-xs leading-tight text-gray-500">Tour Operator</span>
        </span>
      </div>
    </header>
  );
}
