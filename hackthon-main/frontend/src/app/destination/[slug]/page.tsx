"use client";

import { use, useState, useMemo } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Heart, MapPin, Compass, Share2, Mail } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import ImageGallery from "@/components/destinations/image-gallery";
import MatchInfo from "@/components/destinations/match-info";
import WeatherCard from "@/components/destinations/weather-card";
import { getDestinationBySlug, calculateMatchScore } from "@/lib/recommendations";
import { destinations } from "@/lib/mock-data";
import { emptyOnboardingData, type OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "voyager_onboarding_data";
const FAVORITES_KEY = "voyager_favorites";

const fallbackImages: Record<string, string[]> = {
  bali: [
    "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1518361761386-d6fde0b432b4?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1513832275050-72b42560a882?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1473625985634-0c7c3a0a7629?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1533090368676-1fd25485db88?auto=format&fit=crop&w=1600&q=80",
  ],
  kyoto: [
    "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1549880338-6c0dcf2d6b8e?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1575444759186-8039b7c13143?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1584395130296-643ea10a91d5?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1575052114096-d6c95a528986?auto=format&fit=crop&w=1600&q=80",
  ],
  paris: [
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1533136259960-0b1c7f7d4b45?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1541447271481-988123206529?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1516595535715-8b2b2b8b2b2b?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1499613826799-f9c5b8fdd559?auto=format&fit=crop&w=1600&q=80",
  ],
  santorini: [
    "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1464822759287-3e9f4029b996?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1492636703447-e3a5c650919d?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1587313469290-ff3e38e1f4ab?auto=format&fit=crop&w=1600&q=80",
  ],
  "swiss-alps": [
    "https://images.unsplash.com/photo-1527668752968-14dc70a27c95?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1482049698708-74a44c7e6229?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1511497583084-6a3e3b0d1b3b?auto=format&fit=crop&w=1600&q=80",
  ],
  dubai: [
    "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1535998570210-2e4f8599eba8?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1501365291536-8083534f7d1e?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1482582673516-8da5e9f2f574?auto=format&fit=crop&w=1600&q=80",
  ],
  iceland: [
    "https://images.unsplash.com/photo-1476610182048-b716b8518aae?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1506317993423-7c2a3e0e0e3c?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1519046904888-52509f61f611?auto=format&fit=crop&w=1600&q=80",
  ],
};

// Next 16 makes `params` a Promise — must be unwrapped with React.use() in
// a client component. Reading `params.slug` synchronously silently returned
// `undefined` and hit the "not found" fallback.
export default function DestinationPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const initialFavorite = useMemo(() => {
    try {
      const favoritesRaw = typeof window !== "undefined" ? window.localStorage.getItem(FAVORITES_KEY) : null;
      if (favoritesRaw) {
        const favs: string[] = JSON.parse(favoritesRaw);
        return favs.includes(slug);
      }
    } catch {
      // ignore
    }
    return false;
  }, [slug]);

  const [isFavorite, setIsFavorite] = useState(initialFavorite);

  const destination = getDestinationBySlug(slug);
  const preferences = useMemo(() => {
    try {
      const saved = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
      if (saved) {
        return { ...emptyOnboardingData, ...JSON.parse(saved) } as OnboardingData;
      }
    } catch {
      // ignore
    }
    return emptyOnboardingData;
  }, []);

  const matchScore = useMemo(() => {
    if (destination && preferences.travelerTypes.length > 0) {
      return calculateMatchScore(destination, preferences);
    }
    return undefined;
  }, [destination, preferences]);

  const toggleFavorite = () => {
    try {
      const favoritesRaw = localStorage.getItem(FAVORITES_KEY);
      let favs: string[] = [];
      if (favoritesRaw) {
        favs = JSON.parse(favoritesRaw);
      }
      const newFavs = isFavorite ? favs.filter((id) => id !== slug) : [...favs, slug];
      localStorage.setItem(FAVORITES_KEY, JSON.stringify(newFavs));
      setIsFavorite(!isFavorite);
    } catch {
      // ignore
    }
  };

  if (!destination) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="mx-auto max-w-7xl px-4 py-24 text-center">
          <h1 className="text-2xl font-bold text-dark">Destination not found</h1>
          <p className="mt-2 text-gray-600">We couldn&apos;t find the destination you&apos;re looking for.</p>
          <Link href="/discover" className="mt-6 inline-block rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
            Browse Destinations
          </Link>
        </div>
      </div>
    );
  }

  const galleryImages = fallbackImages[destination.slug] || [destination.image];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <div className="mx-auto max-w-7xl px-4 pt-24 pb-12 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/discover" className="text-sm text-gray-500 hover:text-dark">
              Discover
            </Link>
            <span className="text-gray-300">/</span>
            <span className="text-sm font-medium text-dark">{destination.name}</span>
          </div>
          <div className="flex gap-3">
            <button
              onClick={toggleFavorite}
              className={cn(
                "flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all",
                isFavorite
                  ? "border-red-200 bg-red-50 text-red-600"
                  : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
              )}
              aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
            >
              <Heart className={cn("h-4 w-4", isFavorite && "fill-current")} />
              {isFavorite ? "Saved" : "Save"}
            </button>
            <button className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50">
              <Share2 className="h-4 w-4" />
              Share
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-12 lg:grid-cols-3 lg:gap-12">
          <div className="lg:col-span-2">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
              <h1 className="text-3xl font-bold text-dark sm:text-4xl md:text-5xl">{destination.name}</h1>
              <div className="mt-2 flex items-center gap-2">
                <MapPin className="h-5 w-5 text-primary" />
                <span className="text-lg text-gray-600">{destination.country}</span>
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <ImageGallery images={galleryImages} alt={destination.name} />
            </motion.div>
          </div>

          <div className="lg:col-span-1">
            <MatchInfo destination={destination} matchScore={matchScore} />

            <div className="mt-6">
              <WeatherCard place={`${destination.name}, ${destination.country}`} />
            </div>

            <motion.div
              className="mt-6 space-y-3"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Link
                href="/planner"
                className="flex items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-lg transition-all hover:bg-primary/90"
              >
                <Compass className="h-4 w-4" />
                Plan My Trip
              </Link>
              <Link
                href="/register"
                className="flex items-center justify-center gap-2 rounded-full border border-gray-200 bg-white px-6 py-3 text-sm font-medium text-dark transition-colors hover:bg-gray-50"
              >
                <Mail className="h-4 w-4" />
                Get Travel Tips
              </Link>
            </motion.div>
          </div>
        </div>

        <motion.div
          className="mt-12 grid grid-cols-1 gap-12 lg:grid-cols-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div>
            <h2 className="text-2xl font-bold text-dark">About {destination.name}</h2>
            <p className="mt-4 text-gray-600 leading-relaxed">{destination.description}</p>
          </div>

          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-dark">Activities</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {destination.activities.map((activity) => (
                  <span
                    key={activity}
                    className="rounded-full bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary"
                  >
                    {activity.replace("-", " ")}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-dark">Tags</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {destination.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-gray-100 px-3 py-1.5 text-sm text-gray-600">
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {preferences.activities.length > 0 && (
              <motion.div
                className="rounded-2xl border border-gray-100 bg-white p-6"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
              >
                <h3 className="text-lg font-semibold text-dark mb-3">Why this matches you</h3>
                <p className="text-sm text-gray-600">
                  Based on your interest in {preferences.activities.slice(0, 3).join(", ")}, this destination offers activities that align with your travel style.
                </p>
              </motion.div>
            )}
          </div>
        </motion.div>

        <motion.div
          className="mt-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <h2 className="text-2xl font-bold text-dark mb-6">More Like This</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {destinations
              .filter((d) => d.id !== destination.id && d.destinationTypes.some((dt) => destination.destinationTypes.includes(dt)))
              .slice(0, 4)
              .map((d, index) => (
                <Link href={`/destination/${d.slug}`} key={d.id} className="block group">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ y: -4 }}
                    className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm"
                  >
                    <div className="relative aspect-[4/3] overflow-hidden">
                      <ImageGallery images={[d.image]} alt={d.name} />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                      <div className="absolute left-3 top-3">
                        <span className="inline-flex items-center gap-1 rounded-full bg-white/90 px-2.5 py-1 text-xs font-semibold text-dark">
                          <MapPin className="h-3 w-3" />
                          {d.country}
                        </span>
                      </div>
                    </div>
                    <div className="p-4">
                      <h3 className="font-bold text-dark group-hover:text-primary transition-colors">{d.name}</h3>
                      <p className="mt-1 text-sm text-gray-500 line-clamp-2">{d.shortDescription}</p>
                      <div className="mt-3 flex items-center justify-between">
                        <span className="text-sm font-semibold text-dark">${d.estimatedDailyCost}/day</span>
                        {d.budget && (
                          <span className="text-xs text-gray-500 capitalize">{d.budget}</span>
                        )}
                      </div>
                    </div>
                  </motion.div>
                </Link>
              ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
