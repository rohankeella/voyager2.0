import Image from "next/image";
import Link from "next/link";
import type { Destination } from "@/lib/mock-data";

export default function RecommendationCard({ destination }: { destination: Destination }) {
  return (
    <Link
      href={`/destination/${destination.slug}`}
      className="group overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="relative h-28 w-full overflow-hidden bg-gray-100">
        <Image
          src={destination.image}
          alt={destination.name}
          fill
          sizes="(max-width: 640px) 50vw, 220px"
          className="object-cover transition-transform duration-500 group-hover:scale-105"
        />
      </div>
      <div className="p-3.5">
        <p className="text-sm font-bold text-dark">{destination.name}</p>
        <p className="text-xs text-gray-500">{destination.country}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {destination.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium capitalize text-primary">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </Link>
  );
}
