import Link from "next/link";
import { ArrowRight, CalendarDays, Compass, Heart, MapPin, Sparkles } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import DestinationCard from "@/components/destinations/destination-card";
import Hero from "@/components/landing/hero";
import { destinations } from "@/lib/mock-data";

const featuredDestinations = [destinations[0], destinations[1], destinations[4], destinations[13]];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Navbar />
      <main className="flex-1">
        <Hero />

        <section id="how-voyager-works" className="scroll-mt-24 bg-white py-24 sm:py-32">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl text-center">
              <span className="inline-flex rounded-full bg-primary/10 px-4 py-1.5 text-sm font-semibold text-primary">
                A smarter way to plan
              </span>
              <h2 className="mt-6 text-3xl font-bold tracking-tight text-dark sm:text-4xl lg:text-5xl">
                From travel dreams to a journey that feels like yours
              </h2>
              <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-gray-600 sm:text-lg">
                Voyager learns how you like to travel, finds destinations that fit your style, and helps you turn inspiration into a practical day-by-day plan.
              </p>
            </div>

            <div className="mt-16 grid gap-6 md:grid-cols-3">
              <div className="rounded-3xl border border-gray-100 bg-background p-8 shadow-sm">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Sparkles className="h-7 w-7" />
                </div>
                <h3 className="mt-6 text-xl font-bold text-dark">Tell us your style</h3>
                <p className="mt-3 leading-7 text-gray-600">
                  Choose the activities, destinations, budget, seasons, and pace that make a trip exciting for you.
                </p>
              </div>

              <div className="rounded-3xl border border-gray-100 bg-background p-8 shadow-sm">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/10 text-primary">
                  <Compass className="h-7 w-7" />
                </div>
                <h3 className="mt-6 text-xl font-bold text-dark">Discover your matches</h3>
                <p className="mt-3 leading-7 text-gray-600">
                  Explore destinations ranked around your preferences, with clear match scores and useful trip details.
                </p>
              </div>

              <div className="rounded-3xl border border-gray-100 bg-background p-8 shadow-sm">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10 text-accent">
                  <CalendarDays className="h-7 w-7" />
                </div>
                <h3 className="mt-6 text-xl font-bold text-dark">Build your itinerary</h3>
                <p className="mt-3 leading-7 text-gray-600">
                  Organize every day, add activities, rearrange your plans, and keep your trip ideas in one place.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="bg-background py-24 sm:py-32">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-2xl">
                <span className="text-sm font-semibold uppercase tracking-wider text-primary">Curated destinations</span>
                <h2 className="mt-3 text-3xl font-bold tracking-tight text-dark sm:text-4xl">Places our travelers love</h2>
                <p className="mt-4 text-base leading-7 text-gray-600">
                  From tropical islands to cultural cities and mountain escapes, start with destinations made for memorable journeys.
                </p>
              </div>
              <Link
                href="/discover"
                className="inline-flex w-fit items-center gap-2 rounded-full border-2 border-primary px-5 py-3 text-sm font-semibold text-primary transition-colors hover:bg-primary hover:text-primary-foreground sm:w-auto"
              >
                View all destinations
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {featuredDestinations.map((destination, index) => (
                <DestinationCard key={destination.id} destination={destination} index={index} />
              ))}
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden bg-dark py-24 text-white sm:py-32">
          <div
            className="absolute inset-0 bg-cover bg-center opacity-25"
            style={{
              backgroundImage:
                "url('https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=2021&q=80')",
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-dark via-dark/90 to-dark/60" />

          <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="grid gap-12 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
              <div>
                <span className="inline-flex rounded-full bg-white/10 px-4 py-1.5 text-sm font-semibold text-secondary">
                  Personal by design
                </span>
                <h2 className="mt-6 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
                  Your preferences shape every recommendation
                </h2>
                <p className="mt-5 max-w-2xl text-lg leading-8 text-white/75">
                  Voyager connects what you love with where you should go next. Update your profile at any time and your destination matches will evolve with you.
                </p>

                <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                    <p className="text-3xl font-bold text-secondary">10</p>
                    <p className="mt-1 text-sm text-white/70">Preference questions</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                    <p className="text-3xl font-bold text-secondary">18</p>
                    <p className="mt-1 text-sm text-white/70">Destinations to explore</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                    <p className="text-3xl font-bold text-secondary">1</p>
                    <p className="mt-1 text-sm text-white/70">Personal travel plan</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-4 rounded-2xl border border-white/10 bg-white/5 p-5">
                  <MapPin className="mt-1 h-6 w-6 shrink-0 text-secondary" />
                  <div>
                    <h3 className="font-semibold">Destination matching</h3>
                    <p className="mt-1 text-sm leading-6 text-white/70">See why each destination fits your activities, budget, season, and travel pace.</p>
                  </div>
                </div>
                <div className="flex items-start gap-4 rounded-2xl border border-white/10 bg-white/5 p-5">
                  <Heart className="mt-1 h-6 w-6 shrink-0 text-secondary" />
                  <div>
                    <h3 className="font-semibold">Save what inspires you</h3>
                    <p className="mt-1 text-sm leading-6 text-white/70">Keep favorite places close while you compare ideas and plan the details.</p>
                  </div>
                </div>
                <div className="flex items-start gap-4 rounded-2xl border border-white/10 bg-white/5 p-5">
                  <CalendarDays className="mt-1 h-6 w-6 shrink-0 text-secondary" />
                  <div>
                    <h3 className="font-semibold">Plan at your own pace</h3>
                    <p className="mt-1 text-sm leading-6 text-white/70">Create, edit, reorder, and export an itinerary whenever you are ready.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="bg-white py-24 sm:py-32">
          <div className="mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold tracking-tight text-dark sm:text-4xl lg:text-5xl">
              Ready to find your next place?
            </h2>
            <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-gray-600">
              Create your travel profile and let Voyager turn your preferences into a journey worth remembering.
            </p>
            <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
              <Link
                href="/register"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-primary px-8 py-4 text-base font-semibold text-primary-foreground shadow-lg transition-colors hover:bg-primary/90"
              >
                Start planning
                <ArrowRight className="h-5 w-5" />
              </Link>
              <Link
                href="/discover"
                className="inline-flex items-center justify-center rounded-full border-2 border-gray-200 px-8 py-4 text-base font-semibold text-dark transition-colors hover:border-primary hover:text-primary"
              >
                Explore destinations
              </Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
