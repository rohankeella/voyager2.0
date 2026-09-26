"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import Step1 from "@/components/onboarding/step1";
import Step2 from "@/components/onboarding/step2";
import Step3 from "@/components/onboarding/step3";
import Step4 from "@/components/onboarding/step4";
import Step5 from "@/components/onboarding/step5";
import Step6 from "@/components/onboarding/step6";
import Step7 from "@/components/onboarding/step7";
import Step8 from "@/components/onboarding/step8";
import Step9 from "@/components/onboarding/step9";
import Step10 from "@/components/onboarding/step10";
import { emptyOnboardingData, type OnboardingData } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "voyager_onboarding_data";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(0);
  const [data, setData] = useState<OnboardingData>(emptyOnboardingData);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        setData((prev) => ({ ...prev, ...JSON.parse(saved) }));
      }
    } catch {
      // ignore parse errors
    }
  }, []);

  const save = useCallback((next: Partial<OnboardingData>) => {
    setData((prev) => {
      const merged = { ...prev, ...next } as OnboardingData;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
      return merged;
    });
  }, []);

  const totalSteps = 10;

  const goNext = () => setStep((s) => Math.min(s + 1, totalSteps - 1));
  const goBack = () => setStep((s) => Math.max(s - 1, 0));
  const goTo = (index: number) => {
    setDirection(index > step ? 1 : -1);
    setStep(index);
  };

  const handleFinish = () => {
    router.push("/dashboard");
  };

  const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 300 : -300, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -300 : 300, opacity: 0 }),
  };

  const steps = [
    <Step1 key="step1" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step2 key="step2" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step3 key="step3" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step4 key="step4" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step5 key="step5" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step6 key="step6" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step7 key="step7" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step8 key="step8" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step9 key="step9" data={data} save={save} onNext={goNext} onBack={goBack} />,
    <Step10 key="step10" data={data} save={save} onNext={handleFinish} onBack={goBack} />,
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-gray-100 bg-white/80 backdrop-blur-md">
        <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold text-dark">Voyager</span>
            <span className="text-sm text-gray-500">
              Step {step + 1} of {totalSteps}
            </span>
          </div>
          <div className="mt-3 h-2 w-full rounded-full bg-gray-100">
            <motion.div
              className="h-full rounded-full bg-primary"
              animate={{ width: `${((step + 1) / totalSteps) * 100}%` }}
              transition={{ duration: 0.4 }}
            />
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-8 sm:px-6">
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={goBack}
            disabled={step === 0}
            className={cn(
              "flex items-center gap-1 rounded-full px-4 py-2 text-sm font-medium transition-colors",
              step === 0 ? "invisible" : "text-gray-600 hover:bg-gray-100"
            )}
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </button>

          <div className="flex gap-1.5">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <button
                key={i}
                onClick={() => goTo(i)}
                className={cn(
                  "h-2 w-2 rounded-full transition-colors",
                  i === step ? "bg-primary" : "bg-gray-300 hover:bg-gray-400"
                )}
                aria-label={`Go to step ${i + 1}`}
              />
            ))}
          </div>

          <div className="w-16" />
        </div>

        <div className="relative flex-1 overflow-hidden rounded-3xl border border-gray-100 bg-white p-6 sm:p-10">
          <AnimatePresence initial={false} custom={direction} mode="wait">
            <motion.div
              key={step}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="h-full"
            >
              {steps[step]}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
