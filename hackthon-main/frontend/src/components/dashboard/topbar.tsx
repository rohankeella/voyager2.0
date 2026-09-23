"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, Bell, ChevronDown, Settings, LogOut, User as UserIcon } from "lucide-react";
import { notifications } from "@/lib/dashboard-data";

export default function Topbar({ userName = "Traveler" }: { userName?: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const initials = userName
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-gray-100 bg-white/90 px-4 backdrop-blur-sm sm:px-6">
      <div className="relative hidden flex-1 max-w-md sm:block">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          placeholder="Search destinations, trips, activities..."
          className="w-full rounded-full border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-4 text-sm text-dark placeholder:text-gray-400 focus:border-primary focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div className="ml-auto flex items-center gap-2 sm:gap-4">
        <Link
          href="/dashboard/notifications"
          className="relative rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-50 hover:text-dark"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {notifications.length > 0 && (
            <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
              {notifications.length}
            </span>
          )}
        </Link>

        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 transition-colors hover:bg-gray-50"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
              {initials}
            </span>
            <span className="hidden text-left sm:block">
              <span className="block text-sm font-semibold leading-tight text-dark">Hi, {userName}</span>
              <span className="block text-xs leading-tight text-gray-500">Traveler</span>
            </span>
            <ChevronDown className="hidden h-4 w-4 text-gray-400 sm:block" />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 z-20 mt-2 w-48 overflow-hidden rounded-2xl border border-gray-100 bg-white py-1 shadow-lg">
                <Link
                  href="/dashboard/profile"
                  className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                  onClick={() => setMenuOpen(false)}
                >
                  <UserIcon className="h-4 w-4" /> Profile
                </Link>
                <Link
                  href="/dashboard/settings"
                  className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                  onClick={() => setMenuOpen(false)}
                >
                  <Settings className="h-4 w-4" /> Settings
                </Link>
                <Link
                  href="/"
                  className="flex items-center gap-2 border-t border-gray-100 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50"
                  onClick={() => setMenuOpen(false)}
                >
                  <LogOut className="h-4 w-4" /> Log out
                </Link>
              </div>
            </>
          )}
        </div>

        <Link
          href="/dashboard/settings"
          className="hidden rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-50 hover:text-dark sm:block"
          aria-label="Settings"
        >
          <Settings className="h-5 w-5" />
        </Link>
      </div>
    </header>
  );
}
