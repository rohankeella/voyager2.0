"use client";

import { useEffect, useState } from "react";
import { Cloud, CloudRain, Sun, Snowflake, CloudDrizzle, Wind } from "lucide-react";
import { ApiError, travelApi, type ApiWeatherResponse } from "@/lib/api";

// Open-Meteo WMO weather codes → label + icon. Full table: https://open-meteo.com/en/docs
function describe(code: number): { label: string; Icon: typeof Sun } {
  if (code === 0) return { label: "Clear", Icon: Sun };
  if (code <= 3) return { label: "Partly cloudy", Icon: Cloud };
  if (code <= 48) return { label: "Foggy", Icon: Cloud };
  if (code <= 57) return { label: "Drizzle", Icon: CloudDrizzle };
  if (code <= 67) return { label: "Rain", Icon: CloudRain };
  if (code <= 77) return { label: "Snow", Icon: Snowflake };
  if (code <= 82) return { label: "Showers", Icon: CloudRain };
  if (code <= 86) return { label: "Snow showers", Icon: Snowflake };
  return { label: "Thunderstorm", Icon: CloudRain };
}

function shortDay(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { weekday: "short" });
}

export default function WeatherCard({ place }: { place: string }) {
  const [data, setData] = useState<ApiWeatherResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    travelApi
      .weather({ place })
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof ApiError) setError(e.message);
        else setError("Weather backend unreachable");
      });
    return () => {
      cancelled = true;
    };
  }, [place]);

  if (error) {
    return (
      <div className="rounded-2xl border border-gray-100 bg-white p-4 text-sm text-gray-500">
        Weather unavailable — {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="animate-pulse rounded-2xl border border-gray-100 bg-white p-4">
        <div className="h-4 w-24 rounded bg-gray-100" />
        <div className="mt-3 h-8 w-32 rounded bg-gray-100" />
        <div className="mt-4 grid grid-cols-7 gap-2">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="h-16 rounded bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  const current = describe(data.current.weather_code);
  const CurrentIcon = current.Icon;

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-gray-400">Weather</div>
          <div className="mt-1 flex items-center gap-3">
            <CurrentIcon className="h-8 w-8 text-primary" />
            <div>
              <div className="text-2xl font-bold text-dark">
                {Math.round(data.current.temperature_c)}&deg;C
              </div>
              <div className="text-sm text-gray-500">{current.label}</div>
            </div>
          </div>
        </div>
        <div className="text-right text-xs text-gray-400">
          <div className="flex items-center justify-end gap-1">
            <Wind className="h-3 w-3" /> {Math.round(data.current.wind_kph)} km/h
          </div>
          <div className="mt-1">Humidity {data.current.humidity}%</div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-7 gap-2 border-t border-gray-100 pt-4">
        {data.daily.slice(0, 7).map((d) => {
          const { Icon } = describe(d.weather_code);
          return (
            <div key={d.date} className="flex flex-col items-center text-center">
              <div className="text-[11px] font-medium text-gray-500">{shortDay(d.date)}</div>
              <Icon className="mt-1 h-4 w-4 text-gray-600" />
              <div className="mt-1 text-xs font-semibold text-dark">
                {Math.round(d.temp_max)}&deg;
              </div>
              <div className="text-[11px] text-gray-400">{Math.round(d.temp_min)}&deg;</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
