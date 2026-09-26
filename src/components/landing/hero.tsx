"use client";

import Link from "next/link";
import { ArrowDown, ArrowUpRight } from "lucide-react";
import styles from "./landing.module.css";

export default function Hero() {
  return (
    <section className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.heroInner}>
        <div className={styles.heroCopy}>
          <h1 id="hero-title">
            Your next journey,
            <br />
            <em>personalized</em>
            <br />
            for you.
          </h1>

          <p>
            Tell us what you love. We&apos;ll help you discover where to go,
            what to do, and how to experience it.
          </p>

          <div className={styles.actions}>
            <Link href="/register" className={styles.primaryLink}>
              Start Planning
              <ArrowUpRight size={19} aria-hidden="true" />
            </Link>

            <Link href="/discover" className={styles.textLink}>
              Explore Destinations
              <ArrowUpRight size={17} aria-hidden="true" />
            </Link>
          </div>

          <div
            className={styles.heroStats}
            aria-label="Voyager platform highlights"
          >
            <div>
              <strong>100%</strong>
              <span>Dynamic Flexibility</span>
            </div>

            <div>
              <strong>1,200+</strong>
              <span>Guided Travelers</span>
            </div>

            <div>
              <strong>2 Roles</strong>
              <span>Travelers &amp; Operators</span>
            </div>

            <div>
              <strong>99.4%</strong>
              <span>Schedule Integrity</span>
            </div>
          </div>
        </div>

        <a
          href="#destinations"
          className={styles.scrollLink}
        >
          <ArrowDown size={16} aria-hidden="true" />
          A world of possibilities
        </a>
      </div>
    </section>
  );
}