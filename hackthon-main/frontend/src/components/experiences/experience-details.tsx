"use client";

import { useEffect, useState } from "react";
import { Clock, MapPin, Star } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import BackButton from "@/components/ui/back-button";
import { ApiError, experiencesApi, type ApiExperience } from "@/lib/api";
import { categoryNames, ExperienceImage, ExperiencePrice, numeric, safeUrl, strings } from "./experience-card";

export default function ExperienceDetails({ id, initialDate }: { id: string; initialDate: string }) {
  const [result, setResult] = useState<{ key: string; experience?: ApiExperience; error?: string }>();
  const [retry, setRetry] = useState(0), [date, setDate] = useState(initialDate), [travelers, setTravelers] = useState(1);
  const key = `${id}:${retry}`;
  useEffect(() => {
    const controller = new AbortController();
    experiencesApi.get(id, controller.signal).then(experience => setResult({ key, experience })).catch(error => {
      if (!controller.signal.aborted) setResult({ key, error: error instanceof ApiError && error.status === 404 ? "This experience is no longer available." : "We couldn’t load this experience. Please try again." });
    });
    return () => controller.abort();
  }, [id, key]);
  const e = result?.key === key ? result.experience : undefined;
  const a = e?.attributes ?? {};
  const rating = numeric(a.rating), score = numeric(a.recommendation_score);
  const images = [...new Set([a.image_url, ...strings(a.gallery)].filter((v): v is string => typeof v === "string"))];
  const availableDates = strings(a.available_dates), slots = strings(a.time_slots);
  const bookingUrl = a.is_sample === true ? undefined : safeUrl(a.booking_url);
  const weekday = date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? (new Date(`${date}T12:00:00`).getDay() + 6) % 7 : undefined;
  const closed = e && weekday !== undefined && e.hours.length > 0 && !e.hours.some(h => h.day_of_week === weekday);
  return <div className="experience-page"><Navbar /><main className="experience-shell"><BackButton fallbackHref="/experiences" label="Back to experiences" />
    {result?.key !== key ? <div className="experience-state" aria-busy="true"><div className="experience-skeleton w-full"><div /><span /><span /></div><p>Loading experience…</p></div> : result.error ? <div className="experience-state" role="alert"><h1>{result.error}</h1><button className="experience-primary" onClick={() => setRetry(v => v + 1)}>Retry</button></div> : e && <>
      <header className="experience-detail-header"><p className="experience-benefit">{categoryNames[e.category]}</p><h1>{e.title}</h1><p className="experience-muted"><MapPin size={16} aria-hidden="true" />{[e.city, e.country].filter(Boolean).join(", ")}<span>·</span><Clock size={16} aria-hidden="true" />{+(e.duration_mins / 60).toFixed(1)} hours</p>
        {rating !== undefined && rating >= 0 && rating <= 5 && <p className="experience-rating"><Star size={16} />{rating} / 5 {numeric(a.review_count) !== undefined && `(${a.review_count} reviews)`}</p>}
        {score !== undefined && score >= 0 && score <= 100 && <p className="experience-benefit">{score}% match {strings(a.match_reasons).join(" · ")}</p>}
      </header>
      {a.is_sample === true && <p className="experience-sample-note">Sample catalog activity. Prices and descriptions are illustrative; booking is unavailable.</p>}
      <div className="experience-gallery">{images.length ? images.slice(0,3).map((url, i) => <ExperienceImage key={url} src={url} title={`${e.title}${i ? ` — photo ${i + 1}` : ""}`} eager={i === 0} />) : <ExperienceImage src={undefined} title={e.title} />}</div>
      <div className="experience-detail-layout"><div className="experience-detail-copy">
        <section><h2>About this experience</h2><p>{e.description || "The provider hasn’t added a description yet."}</p></section>
        {([ ["Highlights", "highlights"], ["What’s included", "included"], ["What’s excluded", "excluded"] ] as const).map(([title, field]) => <section key={field}><h2>{title}</h2>{strings(a[field]).length ? <ul>{strings(a[field]).map((item, i) => <li key={i}>{item}</li>)}</ul> : <p>Not provided. Confirm with the provider before booking.</p>}</section>)}
        <section><h2>Meeting point</h2><p>{typeof a.meeting_point === "string" ? a.meeting_point : e.address || "The provider hasn’t specified a meeting point."}</p></section>
        <section><h2>Cancellation policy</h2><p>{typeof a.cancellation_policy === "string" ? a.cancellation_policy : a.free_cancellation === true ? "Free cancellation is offered. Confirm the cancellation deadline and terms with the provider." : "Cancellation terms have not been provided."}</p></section>
        <section><h2>Operating hours</h2>{e.hours.length ? <ul>{e.hours.map(h => <li key={h.id}>{["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][h.day_of_week]}: {h.open_time}–{h.close_time}</li>)}</ul> : <p>No restricted operating hours are listed. Confirm your visit with the provider.</p>}<p>Times are local to the destination. Operating hours do not guarantee availability.</p></section>
        <section><h2>Reviews</h2>{strings(a.reviews).length ? strings(a.reviews).map((review, i) => <p key={i}>{review}</p>) : <p>No written reviews have been provided.</p>}</section>
      </div><aside className="experience-booking"><h2>Plan your visit</h2><ExperiencePrice experience={e} travelers={travelers} />
        <label className="experience-label">Preferred date{availableDates.length ? <select value={date} onChange={event => setDate(event.target.value)}><option value="">Choose a date</option>{availableDates.map(d => <option key={d}>{d}</option>)}</select> : <input type="date" value={date} onChange={event => setDate(event.target.value)} />}</label>
        {closed && <p role="status" className="experience-help">The provider’s schedule does not list this day. Choose another date.</p>}
        {slots.length > 0 ? <label className="experience-label">Listed time slots<select>{slots.map(slot => <option key={slot}>{slot}</option>)}</select></label> : <p className="experience-help">Time-slot availability has not been provided.</p>}
        <label className="experience-label">Number of travelers<input type="number" min={1} max={100} value={travelers} onChange={event => setTravelers(Math.max(1, Math.min(100, Math.floor(Number(event.target.value) || 1))))} /></label>
        {bookingUrl ? <><a className="experience-primary" href={bookingUrl} target="_blank" rel="noopener noreferrer">Continue to provider</a><p className="experience-help">Confirm your date, time, travelers and final price on the provider’s website. These selections are estimates, not a reservation.</p></> : <><button disabled className="experience-primary">Online booking unavailable</button><p className="experience-help">This activity has no booking link. No reservation or payment has been made.</p></>}
      </aside></div>
    </>}
  </main></div>;
}
