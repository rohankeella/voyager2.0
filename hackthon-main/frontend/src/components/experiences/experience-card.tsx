"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Check, Clock, ImageOff, MapPin, Star } from "lucide-react";
import type { ApiExperience } from "@/lib/api";

export const categoryNames: Record<string, string> = { CULTURE: "Attractions & culture", OUTDOOR: "Nature & adventure", FOOD: "Food & drink", WORKSHOP: "Workshops", FESTIVAL: "Festivals", NIGHTLIFE: "Nightlife & shows" };
export function amount(value: number, currency: string) {
  try { return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 2 }).format(value); }
  catch { return `${currency} ${value.toFixed(2)}`; }
}
export function numeric(value: unknown): number | undefined { return typeof value === "number" && Number.isFinite(value) ? value : undefined; }
export function strings(value: unknown): string[] { return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : []; }
export function safeUrl(value: unknown): string | undefined {
  if (typeof value !== "string") return;
  try { const url = new URL(value); if (url.protocol === "https:") return url.href; } catch { /* Missing provider URL. */ }
}
export function ExperienceImage({ src, title, eager = false }: { src: unknown; title: string; eager?: boolean }) {
  const [failed, setFailed] = useState(false);
  const url = safeUrl(src);
  return <div className="experience-image">{url && !failed ?
    // Provider images may use arbitrary hosts; use a native image without proxying remote URLs.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={url} alt={title} loading={eager ? "eager" : "lazy"} onError={() => setFailed(true)} /> :
    <span><ImageOff size={28} aria-hidden="true" /> Photo not provided</span>}</div>;
}
export function ExperiencePrice({ experience: e, travelers = 1 }: { experience: ApiExperience; travelers?: number }) {
  const original = numeric(e.attributes.original_price);
  return <div className="experience-price">
    {original !== undefined && original > e.base_cost && <p><del>{amount(original * travelers, e.currency)}</del> <span>Save {Math.round((1 - e.base_cost / original) * 100)}%</span></p>}
    <strong>{amount(e.base_cost * travelers, e.currency)}</strong><small>{travelers === 1 ? " per person" : ` for ${travelers} travelers`}</small>
  </div>;
}
export default function ExperienceCard({ experience: e, date }: { experience: ApiExperience; date: string }) {
  const rating = numeric(e.attributes.rating), score = numeric(e.attributes.recommendation_score);
  return <article className="experience-card">
    <Link href={`/experience/${encodeURIComponent(e.id)}${date ? `?date=${encodeURIComponent(date)}` : ""}`} className="experience-card-link">
      <ExperienceImage src={e.attributes.image_url} title={e.title} />
      <div className="experience-card-body">
        <div className="experience-card-meta"><span>{categoryNames[e.category]}</span>{e.attributes.is_sample === true && <span>Sample</span>}</div>
        <h2>{e.title}</h2><p className="experience-muted"><MapPin size={14} aria-hidden="true" />{e.city}</p>
        {rating !== undefined && rating >= 0 && rating <= 5 && <p className="experience-rating"><Star size={14} aria-hidden="true" />{rating.toFixed(1)} / 5 {numeric(e.attributes.review_count) !== undefined && <span>({String(e.attributes.review_count)} reviews)</span>}</p>}
        <p className="experience-muted"><Clock size={14} aria-hidden="true" />{e.duration_mins < 60 ? `${e.duration_mins} min` : `${+(e.duration_mins / 60).toFixed(1)} hours`}</p>
        {e.attributes.free_cancellation === true && <p className="experience-benefit"><Check size={14} aria-hidden="true" />Free cancellation</p>}
        {e.attributes.instant_confirmation === true && <p className="experience-benefit"><Check size={14} aria-hidden="true" />Instant confirmation</p>}
        {score !== undefined && score >= 0 && score <= 100 && <p className="experience-benefit" title={strings(e.attributes.match_reasons).join(" · ")}>{score}% match</p>}
        <div className="experience-card-footer"><ExperiencePrice experience={e} /><span className="experience-details-link">View details <ArrowUpRight size={16} aria-hidden="true" /></span></div>
      </div>
    </Link>
  </article>;
}
