"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { Heart, MapPin } from "lucide-react";
import type { Destination } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type Props = {
  destination: Destination;
  index?: number;
};

export default function DestinationCard({ destination, index = 0 }: Props) {
  const [isFavorite, setIsFavorite] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      whileHover={{ y: -4 }}
      className="group relative overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm transition-shadow hover:shadow-md"
    >
      <Link href={`/destination/${destination.slug}`} className="block">
        <div className="relative aspect-[4/3] overflow-hidden bg-gray-100">
          <Image
            src={destination.image}
            alt={destination.name}
            fill
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, (max-width: 1280px) 33vw, 25vw"
            className={cn(
              "object-cover transition-transform duration-500 group-hover:scale-105",
              imageLoaded ? "blur-0" : "blur-sm"
            )}
            onLoad={() => setImageLoaded(true)}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />

          <div className="absolute left-4 top-4">
            <span className="inline-flex items-center gap-1 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-dark backdrop-blur-sm">
              <MapPin className="h-3 w-3" />
              {destination.country}
            </span>
          </div>

          {destination.matchScore && (
            <div className="absolute right-4 top-4">
              <span className="inline-flex items-center rounded-full bg-primary/90 px-3 py-1 text-xs font-bold text-white backdrop-blur-sm">
                {destination.matchScore}% Match
              </span>
            </div>
          )}

          <button
            onClick={(e) => {
              e.preventDefault();
              setIsFavorite(!isFavorite);
            }}
            className="absolute bottom-4 right-4 rounded-full bg-white/90 p-2 backdrop-blur-sm transition-colors hover:bg-white"
            aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
          >
            <Heart
              className={cn("h-5 w-5 transition-colors", isFavorite ? "fill-red-500 text-red-500" : "text-gray-600")}
            />
          </button>
        </div>

        <div className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-bold text-dark group-hover:text-primary transition-colors">
                {destination.name}
              </h3>
              <p className="mt-1 line-clamp-2 text-sm text-gray-600">{destination.shortDescription}</p>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {destination.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
              >
                {tag}
              </span>
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-gray-50 pt-4">
            <div>
              <p className="text-xs text-gray-500">Estimated daily cost</p>
              <p className="text-sm font-semibold text-dark">
                ${destination.estimatedDailyCost} <span className="font-normal text-gray-500">/ day</span>
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">Best season</p>
              <p className="text-sm font-medium text-dark capitalize">
                {destination.bestSeason[0] || "Year-round"}
              </p>
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
