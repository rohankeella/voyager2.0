import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import Hero from "@/components/landing/hero";
import DestinationStream from "@/components/landing/destination-stream";
import styles from "@/components/landing/landing.module.css";

export default function Home() {
  return (
    <div className={styles.landing}>
      <Navbar landing />
      <main>
        <Hero />
        <DestinationStream />
        <section id="how-voyager-works" className={styles.how} aria-labelledby="how-title">
          <div className={styles.howIntro}>
            <h2 id="how-title">From travel dreams to a journey that feels like yours</h2>
            <p>Voyager learns how you like to travel, finds destinations that fit your style, and helps you turn inspiration into a practical day-by-day plan.</p>
            <Link href="/register" className={styles.textLink}>Start planning <ArrowUpRight size={17} aria-hidden="true" /></Link>
          </div>
          <ol className={styles.steps}>
            <li><h3>Tell us your style</h3><p>Choose the activities, destinations, budget, seasons, and pace that make a trip exciting for you.</p></li>
            <li><h3>Discover your matches</h3><p>Explore destinations ranked around your preferences, with clear match scores and useful trip details.</p></li>
            <li><h3>Build your itinerary</h3><p>Organize every day, add activities, rearrange your plans, and keep your trip ideas in one place.</p></li>
          </ol>
        </section>
        <section className={styles.personal} aria-labelledby="personal-title">
          <div className={styles.personalImage} role="img" aria-label="A winding road through a mountain landscape" />
          <div className={styles.personalCopy}>
            <h2 id="personal-title">Your preferences shape every recommendation</h2>
            <p>Voyager connects what you love with where you should go next. Update your profile at any time and your destination matches will evolve with you.</p>
            <dl>
              <div><dt>Destination matching</dt><dd>See why each destination fits your activities, budget, season, and travel pace.</dd></div>
              <div><dt>Save what inspires you</dt><dd>Keep favorite places close while you compare ideas and plan the details.</dd></div>
              <div><dt>Plan at your own pace</dt><dd>Create, edit, reorder, and export an itinerary whenever you are ready.</dd></div>
            </dl>
          </div>
        </section>
        <section className={styles.closing}>
          <div className={styles.closingInner}>
            <div><h2>Ready to find your next place?</h2><p>Create your travel profile and let Voyager turn your preferences into a journey worth remembering.</p></div>
            <Link href="/register" className={styles.primaryLink}>Start planning <ArrowUpRight size={18} aria-hidden="true" /></Link>
          </div>
        </section>
      </main>
      <footer className={styles.footer}>
        <Link href="/">Voyager</Link>
        <span>Your next journey, personalized for you.</span>
        <nav aria-label="Footer navigation"><Link href="/discover">Discover</Link><Link href="/operator/overview">For Operators</Link><Link href="/login">Login</Link></nav>
      </footer>
    </div>
  );
}
