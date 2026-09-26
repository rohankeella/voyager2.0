"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Compass, Landmark, Trees, Utensils, Palette, Music, PartyPopper, Search, SlidersHorizontal, X } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import BackButton from "@/components/ui/back-button";
import { experiencesApi, type ApiExperience } from "@/lib/api";
import ExperienceCard, { amount, categoryNames } from "./experience-card";

const icons = { CULTURE: Landmark, OUTDOOR: Trees, FOOD: Utensils, WORKSHOP: Palette, FESTIVAL: PartyPopper, NIGHTLIFE: Music };
const durations = { short: "Under 3 hours", half: "3–6 hours", full: "6–12 hours", day: "12–24 hours", multi: "Multi-day" };
const filterKeys = ["category", "duration", "rating", "freeCancellation", "minPrice", "maxPrice", "currency", "search"];
type Facets = Awaited<ReturnType<typeof experiencesApi.facets>>;

export default function ExperienceList() {
  const params = useSearchParams(), router = useRouter();
  const query = params.toString();
  const dialog = useRef<HTMLDialogElement>(null);
  const [retry, setRetry] = useState(0);
  const [response, setResponse] = useState<{ key: string; rows: ApiExperience[]; error?: string }>();
  const [facets, setFacets] = useState<{ key: string; data: Facets }>();
  const baseParams = new URLSearchParams();
  for (const key of ["city", "q", "date"]) if (params.get(key)) baseParams.set(key, params.get(key)!);
  const base = baseParams.toString(), requestKey = `${query}:${retry}`;
  useEffect(() => {
    const controller = new AbortController();
    const request = new URLSearchParams(query); request.set("limit", "24");
    experiencesApi.search(request, controller.signal).then(rows => setResponse({ key: requestKey, rows }))
      .catch(() => { if (!controller.signal.aborted) setResponse({ key: requestKey, rows: [], error: "We couldn’t load experiences. Please try again." }); });
    return () => controller.abort();
  }, [query, requestKey]);
  useEffect(() => {
    const controller = new AbortController();
    experiencesApi.facets(new URLSearchParams(base), controller.signal).then(data => setFacets({ key: base, data }))
      .catch(() => { /* The main request supplies the retry state. */ });
    return () => controller.abort();
  }, [base, retry]);
  const update = (key: string, value: string | string[]) => {
    const next = new URLSearchParams(query); next.delete(key); next.delete("offset");
    for (const item of Array.isArray(value) ? value : [value]) if (item) next.append(key, item);
    router.replace(`/experiences?${next}`, { scroll: false });
  };
  const toggle = (key: string, value: string) => update(key, params.getAll(key).includes(value) ? params.getAll(key).filter(v => v !== value) : [...params.getAll(key), value]);
  const clear = () => { const next = new URLSearchParams(query); for (const key of [...filterKeys, "offset"]) next.delete(key); router.replace(`/experiences?${next}`, { scroll: false }); };
  const data = facets?.key === base ? facets.data : undefined;
  const prices = data?.prices ?? [];
  const bounds = prices.find(p => p.currency === params.get("currency")) ?? (prices.length === 1 ? prices[0] : undefined);
  const busy = response?.key !== requestKey;
  const rows = busy ? [] : response?.rows ?? [];
  const categories = data?.categories ?? Object.entries(categoryNames).map(([id, name]) => ({ id, name, count: undefined }));
  const active = filterKeys.flatMap(key => params.getAll(key).map(value => ({ key, value })));
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const location = params.get("city") || params.get("q");
  const filters = <>
    <div className="experience-filter-title"><h2>Refine your search</h2><button type="button" onClick={clear}>Clear all</button></div>
    <form key={`search:${params.get("search")}`} onSubmit={e => { e.preventDefault(); update("search", String(new FormData(e.currentTarget).get("search") || "").trim()); }}>
      <label className="experience-label">Search for activities<input name="search" defaultValue={params.get("search") ?? ""} placeholder="Try a walk or workshop" type="search" /></label>
      <button className="experience-text-button" type="submit">Apply search</button>
    </form>
    <fieldset><legend>Cancellation</legend><label className="experience-check"><input type="checkbox" checked={params.get("freeCancellation") === "true"} onChange={e => update("freeCancellation", e.target.checked ? "true" : "")} />Free cancellation</label><p className="experience-help">Choose activities with flexible cancellation.</p></fieldset>
    <fieldset><legend>Price per person</legend>
      {prices.length > 1 && <label className="experience-label">Currency<select value={params.get("currency") ?? ""} onChange={e => {
        const next = new URLSearchParams(query); for (const key of ["currency", "minPrice", "maxPrice", "offset"]) next.delete(key);
        if (e.target.value) next.set("currency", e.target.value); router.replace(`/experiences?${next}`, { scroll: false });
      }}><option value="">Choose a currency</option>{prices.map(p => <option key={p.currency}>{p.currency}</option>)}</select></label>}
      {bounds ? <>
        <div className="experience-price-range"><span>{amount(Number(params.get("minPrice") ?? bounds.min), bounds.currency)}</span><span>{amount(Number(params.get("maxPrice") ?? bounds.max), bounds.currency)}</span></div>
        <label className="experience-range">Minimum price<input type="range" aria-label="Minimum price" min={bounds.min} max={bounds.max} step="any" value={params.get("minPrice") ?? bounds.min} onChange={e => update("minPrice", String(Math.min(Number(e.target.value), Number(params.get("maxPrice") ?? bounds.max))))} /></label>
        <label className="experience-range">Maximum price<input type="range" aria-label="Maximum price" min={bounds.min} max={bounds.max} step="any" value={params.get("maxPrice") ?? bounds.max} onChange={e => update("maxPrice", String(Math.max(Number(e.target.value), Number(params.get("minPrice") ?? bounds.min))))} /></label>
      </> : <p className="experience-help">{prices.length > 1 ? "Select a currency to compare prices." : "Price range appears when activities are available."}</p>}
    </fieldset>
    <fieldset><legend>Categories</legend>{categories.map(c => <label className="experience-check" key={c.id}><input type="checkbox" checked={params.getAll("category").includes(c.id)} onChange={() => toggle("category", c.id)} />{c.name}{c.count !== undefined && <small>{c.count}</small>}</label>)}</fieldset>
    <fieldset><legend>Duration</legend>{Object.entries(durations).map(([id, name]) => <label className="experience-check" key={id}><input type="checkbox" checked={params.getAll("duration").includes(id)} onChange={() => toggle("duration", id)} />{name}</label>)}</fieldset>
    <fieldset><legend>Rating</legend><label className="experience-label">Minimum rating<select value={params.get("rating") ?? ""} onChange={e => update("rating", e.target.value)}><option value="">All ratings</option><option value="4">4+ stars</option><option value="3">3+ stars</option></select></label><p className="experience-help">Rated activities only when a minimum is selected.</p></fieldset>
  </>;
  return <div className="experience-page"><Navbar /><main className="experience-shell">
    <div className="experience-intro"><BackButton fallbackHref="/discover" label="Back to Discover" /><h1>Make room for an experience.</h1><p>Find the places, people and little detours that make a trip yours.</p></div>
    <form className="experience-search" key={base} onSubmit={e => {
      e.preventDefault(); const form = new FormData(e.currentTarget), next = new URLSearchParams();
      for (const key of ["q", "date"]) { const value = String(form.get(key) || "").trim(); if (value) next.set(key, value); }
      router.replace(`/experiences?${next}`, { scroll: false }); setRetry(v => v + 1);
    }}><label><Search size={20} aria-hidden="true" /><span>Destination or activity<input name="q" placeholder="Where will curiosity take you?" defaultValue={location ?? ""} type="search" /></span></label><label><span>Date of activity<input name="date" type="date" defaultValue={params.get("date") ?? ""} /></span></label><button className="experience-primary" type="submit">Search experiences</button></form>
    <nav aria-label="Experience categories" className="experience-categories"><button type="button" aria-pressed={!params.has("category")} onClick={() => update("category", "")}><Compass size={24} />All experiences</button>{categories.map(c => { const Icon = icons[c.id as keyof typeof icons] || Compass; return <button key={c.id} type="button" aria-pressed={params.getAll("category").includes(c.id)} onClick={() => toggle("category", c.id)}><Icon size={24} aria-hidden="true" />{c.name}</button>; })}</nav>
    <nav className="experience-breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><span>{location ? `Activities matching ${location}` : "All experiences"}</span></nav>
    <div className="experience-layout"><aside className="experience-sidebar">{filters}</aside><section className="experience-results" aria-label="Experience results">
      <div className="experience-results-heading"><div><h2>{location ? `Activities matching “${location}”` : "Find your next experience"}</h2><p>{params.get("date") ? `Operating on ${params.get("date")} · Confirm availability with the provider` : "Explore the Voyager activity catalog"}</p></div><label>Sort by<select value={params.get("sort") ?? "popularity"} onChange={e => update("sort", e.target.value)}><option value="popularity">Popularity</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option><option value="rating">Rating</option><option value="recommended">Recommended</option></select></label></div>
      <button className="experience-mobile-filter" onClick={() => dialog.current?.showModal()}><SlidersHorizontal size={17} />Filters{active.length ? ` (${active.length})` : ""}</button>
      {active.length > 0 && <div className="experience-chips">{active.map(({ key, value }) => <button key={`${key}:${value}`} onClick={() => update(key, params.getAll(key).filter(v => v !== value))} aria-label={`Remove ${key} ${value}`}>{key === "category" ? categoryNames[value] ?? value : key === "duration" ? durations[value as keyof typeof durations] : key === "freeCancellation" ? "Free cancellation" : `${key === "minPrice" ? "Min price" : key === "maxPrice" ? "Max price" : key}: ${value}`}<X size={13} /></button>)}<button onClick={clear}>Clear all</button></div>}
      <div aria-live="polite" aria-busy={busy}>
        {busy ? <div className="experience-grid" aria-label="Loading experiences">{Array.from({ length: 6 }, (_, i) => <div className="experience-skeleton" key={i}><div /><span /><span /><span /></div>)}</div> : response?.error ? <div className="experience-state" role="alert"><h2>We couldn’t load experiences.</h2><p>Please try again.</p><button className="experience-primary" onClick={() => setRetry(v => v + 1)}>Retry</button></div> : rows.length === 0 ? <div className="experience-state"><Compass size={36} /><h2>No experiences found</h2><p>Try changing your filters or destination.</p><button className="experience-primary" onClick={clear}>Clear filters</button><Link href="/experiences">Browse all experiences</Link></div> : <><p className="experience-count">Showing {offset + 1}–{offset + rows.length} activities</p><div className="experience-grid">{rows.map(e => <ExperienceCard key={e.id} experience={e} date={params.get("date") ?? ""} />)}</div></>}
      </div>
      {!busy && !response?.error && (offset > 0 || rows.length === 24) && <div className="experience-pagination"><button disabled={offset === 0} onClick={() => update("offset", String(Math.max(0, offset - 24)))}>Previous</button><button disabled={rows.length < 24} onClick={() => update("offset", String(offset + 24))}>Next</button></div>}
    </section></div>
    <dialog ref={dialog} className="experience-filter-dialog" aria-label="Refine your search"><button className="experience-dialog-close" aria-label="Close filters" onClick={() => dialog.current?.close()}><X size={20} /></button>{filters}<button className="experience-primary" onClick={() => dialog.current?.close()}>Show results</button></dialog>
  </main></div>;
}
