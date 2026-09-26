"use client";

/**
 * DTO-P3 Phase 7 — Guide onboarding portal.
 *
 * Signed-in users register (or update) their public guide profile: expertise
 * tags, home coordinates, radius, hourly rate, languages, bio. Doubles as
 * "edit" — POST is upsert so re-submitting overwrites.
 */

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, MapPin, UserCheck, CheckCircle2 } from "lucide-react";
import { guidesApi, ApiError, type GuideProfile, type GuideStatus, getStoredUser } from "@/lib/api";
import { cn } from "@/lib/utils";

const SUGGESTED_TAGS = [
  "art",
  "food",
  "history",
  "architecture",
  "photography",
  "hiking",
  "nightlife",
  "shopping",
  "spirituality",
  "wildlife",
  "beaches",
  "adventure",
];

const SUGGESTED_LANGS = ["English", "Hindi", "French", "Spanish", "Japanese", "German", "Mandarin"];

export default function GuideRegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [displayName, setDisplayName] = useState("");
  const [headline, setHeadline] = useState("");
  const [bio, setBio] = useState("");
  const [homeCity, setHomeCity] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [homeLat, setHomeLat] = useState<number | "">("");
  const [homeLng, setHomeLng] = useState<number | "">("");
  const [radiusKm, setRadiusKm] = useState<number>(25);
  const [hourlyRate, setHourlyRate] = useState<number>(35);
  const [minHours, setMinHours] = useState<number>(2);
  const [tags, setTags] = useState<Set<string>>(new Set());
  const [languages, setLanguages] = useState<Set<string>>(new Set(["English"]));
  const [status, setStatus] = useState<GuideStatus>("active");

  useEffect(() => {
    (async () => {
      const user = getStoredUser();
      if (!user) {
        router.push("/login?next=/guides/register");
        return;
      }
      try {
        const g: GuideProfile = await guidesApi.getMe();
        setDisplayName(g.display_name);
        setHeadline(g.headline ?? "");
        setBio(g.bio ?? "");
        setHomeCity(g.home_city ?? "");
        setCountryCode(g.country_code ?? "");
        setHomeLat(g.home_lat);
        setHomeLng(g.home_lng);
        setRadiusKm(g.radius_km);
        setHourlyRate(g.hourly_rate_usd);
        setMinHours(g.min_hours);
        setTags(new Set(g.tags));
        setLanguages(new Set(g.languages.length ? g.languages : ["English"]));
        setStatus(g.status);
      } catch (e) {
        // 404 is fine — user hasn't registered yet
        if (!(e instanceof ApiError && e.status === 404)) {
          setError(e instanceof Error ? e.message : "Load failed");
        }
        setDisplayName(user.full_name || "");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const canSave = useMemo(
    () =>
      !!displayName.trim() &&
      typeof homeLat === "number" &&
      typeof homeLng === "number" &&
      radiusKm > 0 &&
      hourlyRate > 0,
    [displayName, homeLat, homeLng, radiusKm, hourlyRate],
  );

  const toggle = <T,>(set: Set<T>, item: T): Set<T> => {
    const next = new Set(set);
    if (next.has(item)) next.delete(item);
    else next.add(item);
    return next;
  };

  const useMyLocation = () => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setError("Geolocation not supported in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setHomeLat(Number(pos.coords.latitude.toFixed(4)));
        setHomeLng(Number(pos.coords.longitude.toFixed(4)));
      },
      (err) => setError(`Geolocation: ${err.message}`),
      { enableHighAccuracy: false, timeout: 5000 },
    );
  };

  const submit = async () => {
    if (!canSave || typeof homeLat !== "number" || typeof homeLng !== "number") return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await guidesApi.upsertMe({
        display_name: displayName.trim(),
        headline: headline.trim() || null,
        bio: bio.trim() || null,
        home_lat: homeLat,
        home_lng: homeLng,
        home_city: homeCity.trim() || null,
        country_code: countryCode.trim().slice(0, 4) || null,
        radius_km: radiusKm,
        tags: Array.from(tags),
        languages: Array.from(languages),
        hourly_rate_usd: hourlyRate,
        min_hours: minHours,
        status,
      });
      setSaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 text-sm text-gray-500">
        Loading guide profile…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-100 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:border-primary hover:text-primary"
              aria-label="Back"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
                <UserCheck className="h-4 w-4" />
              </span>
              <div>
                <h1 className="text-sm font-bold text-dark">Guide Marketplace</h1>
                <p className="text-[11px] text-gray-500">Register or update your public guide profile</p>
              </div>
            </div>
          </div>
          <Link
            href="/guides/dashboard"
            className="hidden rounded-full border border-gray-200 px-3 py-1 text-xs font-semibold text-gray-500 hover:border-primary hover:text-primary sm:inline-block"
          >
            My bookings →
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-5 p-4 lg:p-6">
        <Section title="Public identity">
          <Field label="Display name">
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} className={inputCls} placeholder="Ada Lovelace" />
          </Field>
          <Field label="Headline" hint="1 line shown in search results.">
            <input value={headline} onChange={(e) => setHeadline(e.target.value)} className={inputCls} placeholder="French bistro history since 2015" />
          </Field>
          <Field label="Bio">
            <textarea value={bio} onChange={(e) => setBio(e.target.value)} rows={3} className={cn(inputCls, "resize-y")} />
          </Field>
        </Section>

        <Section title="Where you guide">
          <Field label="Home city">
            <input value={homeCity} onChange={(e) => setHomeCity(e.target.value)} className={inputCls} placeholder="Paris" />
          </Field>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Country code (2-4 chars)">
              <input value={countryCode} onChange={(e) => setCountryCode(e.target.value)} className={inputCls} placeholder="FR" />
            </Field>
            <Field label="Latitude">
              <input
                type="number"
                step="0.0001"
                value={homeLat}
                onChange={(e) => setHomeLat(e.target.value === "" ? "" : Number(e.target.value))}
                className={inputCls}
                placeholder="48.8566"
              />
            </Field>
            <Field label="Longitude">
              <input
                type="number"
                step="0.0001"
                value={homeLng}
                onChange={(e) => setHomeLng(e.target.value === "" ? "" : Number(e.target.value))}
                className={inputCls}
                placeholder="2.3522"
              />
            </Field>
          </div>
          <button
            type="button"
            onClick={useMyLocation}
            className="inline-flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:border-primary hover:text-primary"
          >
            <MapPin className="h-3 w-3" /> Use my current location
          </button>
          <Field label={`Operating radius: ${radiusKm} km`}>
            <input
              type="range"
              min={1}
              max={100}
              step={1}
              value={radiusKm}
              onChange={(e) => setRadiusKm(Number(e.target.value))}
              className="w-full"
            />
          </Field>
        </Section>

        <Section title="Expertise">
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_TAGS.map((t) => (
              <button
                key={t}
                onClick={() => setTags((s) => toggle(s, t))}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium",
                  tags.has(t)
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-gray-200 text-gray-600 hover:border-primary",
                )}
              >
                {t}
              </button>
            ))}
          </div>
          <Field label="Languages">
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_LANGS.map((l) => (
                <button
                  key={l}
                  onClick={() => setLanguages((s) => toggle(s, l))}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs font-medium",
                    languages.has(l)
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-gray-200 text-gray-600 hover:border-primary",
                  )}
                >
                  {l}
                </button>
              ))}
            </div>
          </Field>
        </Section>

        <Section title="Pricing">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Hourly rate (USD)">
              <input type="number" min={5} step={5} value={hourlyRate} onChange={(e) => setHourlyRate(Number(e.target.value))} className={inputCls} />
            </Field>
            <Field label="Minimum session (hours)">
              <input type="number" min={1} max={12} value={minHours} onChange={(e) => setMinHours(Number(e.target.value))} className={inputCls} />
            </Field>
          </div>
          <p className="text-[11px] text-gray-500">
            Escrow release: your payout accrues on <code className="font-mono">acc_guide_escrow</code> and clears after
            session completion.
          </p>
        </Section>

        <Section title="Availability">
          <div className="flex gap-2">
            {(["active", "paused", "offline"] as GuideStatus[]).map((s) => (
              <button
                key={s}
                onClick={() => setStatus(s)}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium capitalize",
                  status === s ? "border-primary bg-primary/10 text-primary" : "border-gray-200 text-gray-600 hover:border-primary",
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </Section>

        <div className="sticky bottom-0 -mx-4 border-t border-gray-100 bg-white/95 p-3 backdrop-blur lg:mx-0 lg:rounded-2xl lg:border lg:p-4">
          {error && <div className="mb-2 rounded-lg bg-red-50 p-2 text-xs text-red-700">{error}</div>}
          <div className="flex items-center justify-between">
            {saved ? (
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700">
                <CheckCircle2 className="h-3.5 w-3.5" /> Saved · you're live in the marketplace
              </span>
            ) : (
              <span className="text-[11px] text-gray-500">
                {canSave ? "Ready to save." : "Fill in name, coordinates, radius and rate to save."}
              </span>
            )}
            <button
              onClick={submit}
              disabled={!canSave || saving}
              className={cn(
                "flex items-center gap-1 rounded-full px-4 py-2 text-xs font-semibold text-white",
                canSave && !saving ? "bg-primary hover:bg-primary/90" : "bg-gray-300",
              )}
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Save profile
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

const inputCls =
  "w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-dark focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
      <h2 className="text-[11px] font-semibold uppercase tracking-wider text-primary">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs font-semibold text-gray-600">{label}</label>
      {hint && <p className="mt-0.5 text-[10px] text-gray-400">{hint}</p>}
      <div className="mt-1">{children}</div>
    </div>
  );
}
