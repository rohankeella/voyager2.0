"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

export default function BackButton({ fallbackHref = "/discover", label = "Back" }: { fallbackHref?: string; label?: string }) {
  const router = useRouter();
  return <button type="button" onClick={() => {
    // Navigation API excludes inaccessible / blank entries from usable history.
    const navigation = (window as Window & { navigation?: { canGoBack: boolean } }).navigation;
    if (navigation?.canGoBack ?? (window.history.length > 1)) router.back();
    else router.replace(fallbackHref);
  }} className="inline-flex min-h-11 items-center gap-2 rounded-lg px-2 text-sm font-medium text-primary hover:bg-primary/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
    <ArrowLeft size={17} aria-hidden="true" />{label}
  </button>;
}
