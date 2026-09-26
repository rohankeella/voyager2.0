import ExperienceDetails from "@/components/experiences/experience-details";
import "../../experiences/experiences.css";

export const metadata = { title: "Experience details | Voyager" };
export default async function ExperiencePage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ date?: string }> }) {
  const { id } = await params;
  const { date } = await searchParams;
  return <ExperienceDetails id={id} initialDate={date ?? ""} />;
}
