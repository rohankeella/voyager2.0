"use client";

/**
 * DTO-P3 Phase 7 — Guide's incoming-bookings dashboard.
 *
 * Shows requested / confirmed / declined sessions. Accepting locks the
 * time slot server-side; a subsequent overlapping request is refused.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, RefreshCw, CheckCircle2, XCircle, Clock, MapPin } from "lucide-react";
import {
  guidesApi,
  ApiError,
  type GuideBooking,
  type GuideBookingStatus,
  type GuideProfile,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const FILTERS: { label: string; value: GuideBookingStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Requested", value: "requested" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Declined", value: "declined" },
];

export default function GuideDashboardPage() {
  const [profile, setProfile] = useState<GuideProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [bookings, setBookings] = useState<GuideBooking[]>([]);
  const [filter, setFilter] = useState<GuideBookingStatus | "all">("all");
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const rows = await guidesApi.myBookings(filter === "all" ? undefined : filter);
      setBookings(rows);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        // no guide profile yet
      } else {
        setError(e instanceof Error ? e.message : "Load failed");
      }
    } finally {
      setRefreshing(false);
    }
  }, [filter]);

  useEffect(() => {
    (async () => {
      setProfileLoading(true);
      try {
        setProfile(await guidesApi.getMe());
      } catch {
        setProfile(null);
      } finally {
        setProfileLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (profile) load();
  }, [profile, load]);

  const accept = async (b: GuideBooking) => {
    try {
      await guidesApi.accept(b.id);
      load();
    } catch (e) {
      alert(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Accept failed");
    }
  };
  const decline = async (b: GuideBooking) => {
    const reason = window.prompt("Decline reason (optional):") ?? "";
    try {
      await guidesApi.decline(b.id, reason || undefined);
      load();
    } catch (e) {
      alert(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Decline failed");
    }
  };

  if (profileLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 text-sm text-gray-500">
        Loading…
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md rounded-3xl border border-gray-100 bg-white p-8 text-center shadow-sm">
          <h1 className="text-lg font-bold text-dark">No guide profile yet</h1>
          <p className="mt-2 text-sm text-gray-500">
            Register once and travelers can start requesting your sessions.
          </p>
          <Link
            href="/guides/register"
            className="mt-5 inline-block rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
          >
            Register as a guide →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-100 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:border-primary hover:text-primary"
              aria-label="Back"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <h1 className="text-sm font-bold text-dark">{profile.display_name}</h1>
              <p className="text-[11px] text-gray-500">
                ${profile.hourly_rate_usd}/hr · {profile.home_city ?? "Guide"} · {profile.tags.length} expertise tag{profile.tags.length === 1 ? "" : "s"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/guides/register"
              className="rounded-full border border-gray-200 px-3 py-1 text-xs font-semibold text-gray-500 hover:border-primary hover:text-primary"
            >
              Edit profile
            </Link>
            <button
              onClick={load}
              disabled={refreshing}
              className="flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1 text-xs font-semibold text-gray-500 hover:border-primary hover:text-primary disabled:opacity-40"
            >
              <RefreshCw className={refreshing ? "h-3 w-3 animate-spin" : "h-3 w-3"} /> Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-4 p-4 lg:p-6">
        <div className="flex gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-semibold",
                filter === f.value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-gray-200 text-gray-500 hover:border-primary hover:text-primary",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {error && <div className="rounded-lg bg-red-50 p-2 text-xs text-red-700">{error}</div>}

        {bookings.length === 0 ? (
          <div className="rounded-2xl border-2 border-dashed border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
            No bookings in this view.
          </div>
        ) : (
          <div className="space-y-3">
            {bookings.map((b) => (
              <BookingCard key={b.id} b={b} onAccept={() => accept(b)} onDecline={() => decline(b)} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function BookingCard({
  b,
  onAccept,
  onDecline,
}: {
  b: GuideBooking;
  onAccept: () => void;
  onDecline: () => void;
}) {
  const start = new Date(b.start_at);
  const end = new Date(b.end_at);
  const dur = Math.max(0.5, (end.getTime() - start.getTime()) / 3600000);
  const isReq = b.status === "requested";
  const statusMeta: Record<GuideBookingStatus, { tone: string; label: string; Icon: React.ComponentType<{ className?: string }> }> = {
    requested: { tone: "bg-amber-50 text-amber-700", label: "Requested", Icon: Clock },
    confirmed: { tone: "bg-emerald-50 text-emerald-700", label: "Confirmed · slot locked", Icon: CheckCircle2 },
    declined: { tone: "bg-gray-100 text-gray-500", label: "Declined", Icon: XCircle },
    cancelled: { tone: "bg-gray-100 text-gray-500", label: "Cancelled", Icon: XCircle },
    completed: { tone: "bg-sky-50 text-sky-700", label: "Completed", Icon: CheckCircle2 },
  };
  const meta = statusMeta[b.status];
  const StatusIcon = meta.Icon;

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider", meta.tone)}>
            <StatusIcon className="h-3 w-3" />
            {meta.label}
          </div>
          <h3 className="mt-1.5 truncate text-sm font-semibold text-dark">{b.title}</h3>
          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" /> {start.toLocaleString()} → {end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · {dur.toFixed(1)}h
            </span>
            {b.location_label && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" /> {b.location_label}
              </span>
            )}
          </div>
          {b.tags.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1 text-[10px]">
              {b.tags.map((t) => (
                <span key={t} className="rounded-full bg-gray-100 px-1.5 py-0.5 text-gray-600">
                  {t}
                </span>
              ))}
            </div>
          )}
          {b.note && <p className="mt-2 rounded-lg bg-gray-50 p-2 text-[11px] text-gray-600">{b.note}</p>}
        </div>
        <div className="text-right">
          <div className="text-sm font-bold text-dark">${b.total_usd.toFixed(0)}</div>
          <div className="text-[10px] text-gray-400">${b.rate_usd.toFixed(0)}/hr</div>
        </div>
      </div>

      {isReq && (
        <div className="mt-3 flex items-center justify-end gap-2">
          <button
            onClick={onDecline}
            className="rounded-full border border-gray-200 px-3 py-1 text-xs font-semibold text-gray-600 hover:border-red-500 hover:text-red-600"
          >
            Decline
          </button>
          <button
            onClick={onAccept}
            className="rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-700"
          >
            Accept · lock slot
          </button>
        </div>
      )}
    </div>
  );
}
