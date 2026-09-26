"use client";

import { useState } from "react";
import { Plane, Search, Loader2 } from "lucide-react";
import { ApiError, travelApi, type ApiFlightOffer } from "@/lib/api";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

// ISO 8601 duration like "PT9H45M" → "9h 45m"
function formatDuration(iso: string): string {
  const m = /PT(?:(\d+)H)?(?:(\d+)M)?/.exec(iso);
  if (!m) return iso;
  const h = m[1] ? `${m[1]}h ` : "";
  const min = m[2] ? `${m[2]}m` : "";
  return `${h}${min}`.trim();
}

type Props = {
  defaultDestination?: string;
  defaultDepartureDate?: string;
  defaultAdults?: number;
};

export default function FlightSearch({
  defaultDestination = "",
  defaultDepartureDate = "",
  defaultAdults = 1,
}: Props) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState(defaultDestination);
  const [departureDate, setDepartureDate] = useState(defaultDepartureDate);
  const [adults, setAdults] = useState(defaultAdults);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configured, setConfigured] = useState(true);
  const [offers, setOffers] = useState<ApiFlightOffer[] | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!origin || !destination || !departureDate) return;
    setLoading(true);
    setError(null);
    setOffers(null);
    try {
      const data = await travelApi.flights({
        originCity: origin,
        destinationCity: destination,
        departureDate,
        adults,
      });
      setOffers(data.offers);
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 503) setConfigured(false);
        setError(e.message);
      } else {
        setError("Backend unreachable");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Plane className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-dark">Find a flight</h3>
      </div>

      <form onSubmit={submit} className="grid grid-cols-1 gap-3 sm:grid-cols-5">
        <input
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          placeholder="From (e.g. Delhi)"
          className="rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none sm:col-span-1"
          required
        />
        <input
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          placeholder="To (e.g. Paris)"
          className="rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none sm:col-span-1"
          required
        />
        <input
          type="date"
          value={departureDate}
          onChange={(e) => setDepartureDate(e.target.value)}
          className="rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none sm:col-span-1"
          required
        />
        <input
          type="number"
          min={1}
          max={9}
          value={adults}
          onChange={(e) => setAdults(Number(e.target.value))}
          className="rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none sm:col-span-1"
        />
        <button
          type="submit"
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-70 sm:col-span-1"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          Search
        </button>
      </form>

      {!configured && (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
          Flight search is offline — add <code>AMADEUS_CLIENT_ID</code> and{" "}
          <code>AMADEUS_CLIENT_SECRET</code> to <code>backend/.env</code>.
        </div>
      )}

      {error && configured && (
        <div className="mt-4 text-xs text-gray-500">Couldn&rsquo;t load flights — {error}</div>
      )}

      {offers && offers.length === 0 && (
        <div className="mt-4 text-xs text-gray-500">No flights found for those dates.</div>
      )}

      {offers && offers.length > 0 && (
        <ul className="mt-4 divide-y divide-gray-100">
          {offers.slice(0, 6).map((o) => {
            const itin = o.itineraries[0];
            const first = itin.segments[0];
            const last = itin.segments[itin.segments.length - 1];
            const stops = itin.segments.length - 1;
            return (
              <li key={o.id} className="flex items-center justify-between py-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-dark">
                    {first.departure_iata} → {last.arrival_iata}
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatTime(first.departure_at)} – {formatTime(last.arrival_at)} ·{" "}
                    {formatDuration(itin.duration)} ·{" "}
                    {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
                  </div>
                  <div className="text-[11px] text-gray-400">
                    {first.carrier_code} {first.number}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-primary">
                    {o.currency} {Number(o.total).toLocaleString()}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
