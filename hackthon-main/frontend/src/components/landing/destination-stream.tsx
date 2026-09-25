"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, MapPin, Pause, Play } from "lucide-react";
import { ImageStreamHero } from "@/components/ui/image-stream-hero";
import { destinations } from "@/lib/mock-data";
import styles from "./landing.module.css";

const places = [destinations[0], destinations[1], destinations[3], destinations[4], destinations[2], destinations[13]];
const images = destinations.map(place => ({ src: place.image.replace("w=1600", "w=640"), alt: `${place.name}, ${place.country}` }));
const leftImages = images.slice(0, 9);
const rightImages = images.slice(9);

export default function DestinationStream() {
  const [paused, setPaused] = useState(false);
  return (
    <section id="destinations" className={styles.streamSection} aria-labelledby="destinations-title">
      <ImageStreamHero images={leftImages} rightImages={rightImages} speed={28} axis={52} paused={paused} className={styles.stream}>
        <div className={styles.streamContent}>
          <h2 id="destinations-title">Places our travelers love</h2>
          <div className={styles.streamBottom}>
            <p>From tropical islands to cultural cities and mountain escapes, start with destinations made for memorable journeys.</p>
            <Link href="/discover" className={styles.textLink}>View all destinations <ArrowUpRight size={17} aria-hidden="true" /></Link>
          </div>
        </div>
        <button className={styles.pauseStream} onClick={() => setPaused(!paused)} aria-label={paused ? "Play destination animation" : "Pause destination animation"} aria-pressed={paused}>
          {paused ? <Play size={16} aria-hidden="true" /> : <Pause size={16} aria-hidden="true" />}
        </button>
      </ImageStreamHero>
      <nav className={styles.places} aria-label="Featured destinations">
        {places.map(place => <Link key={place.id} href={`/destination/${place.slug}`}><MapPin size={13} aria-hidden="true" />{place.name}</Link>)}
      </nav>
    </section>
  );
}
