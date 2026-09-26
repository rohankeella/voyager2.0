import { Suspense } from "react";
import ExperienceList from "@/components/experiences/experience-list";
import "./experiences.css";

export const metadata = { title: "Experiences & activities | Voyager" };
export default function ExperiencesPage() {
  return <Suspense fallback={<main className="experience-shell" aria-busy="true">Loading experiences…</main>}><ExperienceList /></Suspense>;
}
