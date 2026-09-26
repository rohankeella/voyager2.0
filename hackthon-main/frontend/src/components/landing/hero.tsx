"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowDown, ArrowUpRight } from "lucide-react";
import styles from "./landing.module.css";

const OrbitDeliveryHero = dynamic(() => import("@/components/ui/orbit-delivery-hero"), {
  ssr: false,
  loading: () => <div className={styles.worldLoading}>Your little world is taking shape…</div>,
});

export default function Hero() {
  return (
    <section className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.heroInner}>
        <div className={styles.heroCopy}>
          <h1 id="hero-title">Your next journey,<br /><em>personalized</em><br />for you.</h1>
          <p>Tell us what you love. We&apos;ll help you discover where to go, what to do, and how to experience it.</p>
          <div className={styles.actions}>
            <Link href="/register" className={styles.primaryLink}>Start Planning <ArrowUpRight size={19} aria-hidden="true" /></Link>
            <Link href="/discover" className={styles.textLink}>Explore Destinations <ArrowUpRight size={17} aria-hidden="true" /></Link>
          </div>
        </div>
        <div className={styles.world}><OrbitDeliveryHero /></div>
        <a href="#destinations" className={styles.scrollLink}><ArrowDown size={16} aria-hidden="true" /> A world of possibilities</a>
      </div>
    </section>
  );
}
