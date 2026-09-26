"use client";

import { useEffect, useState } from "react";
import { BedDouble, ExternalLink } from "lucide-react";
import { ApiError, travelApi, type ApiHotelOffer } from "@/lib/api";

type Props = {
  city: string;
  checkIn?: string;
  checkOut?: string;
  adults?: number;
};

export default function HotelOffers({ city, checkIn, checkOut, adults = 2 }: Props) {
  const [offers, setOffers] = useState<ApiHotelOffer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [configured, setConfigured] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    setOffers(null);
    setError(null);

    travelApi
      .hotels({ city, checkIn, checkOut, adults })
      .then((data) => {
        if (!cancelled) setOffers(data.offers);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof ApiError) {
          if (e.status === 503) setConfigured(false);
          setError(e.message);
        } else {
          setError("Backend unreachable");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [city, checkIn, checkOut, adults]);

  if (!configured) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        Hotel search is offline — add <code className="rounded bg-amber-100 px-1">AMADEUS_CLIENT_ID</code> and{" "}
        <code className="rounded bg-amber-100 px-1">AMADEUS_CLIENT_SECRET</code> to <code>backend/.env</code> and
        restart the backend.
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-gray-100 bg-white p-4 text-sm text-gray-500">
        No hotel offers loaded — {error}
      </div>
    );
  }

  if (!offers) {
    return (
      <div className="animate-pulse rounded-2xl border border-gray-100 bg-white p-4">
        <div className="h-4 w-32 rounded bg-gray-100" />
        <div className="mt-3 space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-14 rounded bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  const available = offers.filter((o) => o.available && o.offers.length > 0);

  if (available.length === 0) {
    return (
      <div className="rounded-2xl border border-gray-100 bg-white p-4 text-sm text-gray-500">
        No available hotel offers for {city} on these dates.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <BedDouble className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-dark">Live hotel offers in {city}</h3>
      </div>
      <ul className="mt-4 divide-y divide-gray-100">
        {available.slice(0, 6).map((o) => {
          const offer = o.offers[0];
          return (
            <li key={o.hotel_id} className="flex items-start justify-between gap-4 py-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-dark">{o.hotel_name}</div>
                {offer.room_description && (
                  <div className="mt-0.5 line-clamp-2 text-xs text-gray-500">
                    {offer.room_description}
                  </div>
                )}
                <div className="mt-1 text-[11px] text-gray-400">
                  {offer.check_in_date} → {offer.check_out_date}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <div className="text-sm font-bold text-primary">
                  {offer.price.currency} {Number(offer.price.total).toLocaleString()}
                </div>
                <div className="mt-1 text-[11px] text-gray-400">total stay</div>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 flex items-center gap-1 text-[11px] text-gray-400">
        <ExternalLink className="h-3 w-3" /> Powered by Amadeus Self-Service
      </p>
    </div>
  );
}
