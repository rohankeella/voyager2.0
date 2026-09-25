"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform, useReducedMotion, AnimatePresence } from "framer-motion";
import { Compass, Menu, X } from "lucide-react";

const navLinks = [
  { href: "/discover", label: "Discover" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/discover", label: "Destinations" },
  { href: "/discover", label: "Experiences" },
  { href: "/", label: "About" },
];

export default function Navbar({ landing = false }: { landing?: boolean }) {
  const [isOpen, setIsOpen] = useState(false);
  const reducedMotion = useReducedMotion();
  const { scrollY } = useScroll();
  const backgroundColor = useTransform(scrollY, [0, 100], ["rgba(255,255,255,0)", "rgba(255,255,255,0.85)"]);
  const backdropBlur = useTransform(scrollY, [0, 100], ["blur(0px)", "blur(12px)"]);

  const linkClass = "text-sm font-medium text-dark transition-colors hover:text-primary";
  const links = landing ? [
    { href: "/discover", label: "Discover" },
    { href: "#destinations", label: "Destinations" },
    { href: "#how-voyager-works", label: "How it works" },
  ] : navLinks;

  return (
    <motion.nav
      className="fixed top-0 left-0 right-0 z-50 border-b border-transparent transition-colors"
      style={{
        backgroundColor: landing ? "#f7faf7" : backgroundColor,
        backdropFilter: landing ? "none" : backdropBlur,
      }}
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className={`flex items-center justify-between ${landing ? "h-20" : "h-16"}`}>
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2">
              {landing && <Compass className="h-6 w-6 text-primary" aria-hidden="true" />}
              <span className="text-xl font-bold tracking-tight text-dark">
                Voyager
              </span>
            </Link>
            <div className={`hidden items-center gap-6 ${landing ? "lg:flex" : "md:flex"}`}>
              {links.map((link) => (
                <Link key={link.label} href={link.href} className={linkClass}>
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          <div className={`hidden items-center gap-3 ${landing ? "lg:flex" : "md:flex"}`}>
            <Link
              href="/operator/overview"
              className="rounded-full px-4 py-2 text-sm font-medium text-gray-500 transition-colors hover:bg-gray-100 hover:text-dark"
            >
              For Operators
            </Link>
            <Link
              href="/login"
              className="rounded-full px-4 py-2 text-sm font-medium text-dark transition-colors hover:bg-gray-100"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Get Started
            </Link>
          </div>

          <button
            className={`${landing ? "lg:hidden" : "md:hidden"} rounded-lg p-2 text-gray-600 hover:bg-gray-100`}
            onClick={() => setIsOpen(!isOpen)}
            aria-label="Toggle menu"
            aria-expanded={isOpen}
            aria-controls="mobile-navigation"
          >
            {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            id="mobile-navigation"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={reducedMotion ? { duration: 0 } : undefined}
            className={`${landing ? "lg:hidden" : "md:hidden"} border-t border-gray-100 bg-white/95 backdrop-blur-md`}
          >
            <div className="space-y-1 px-4 pb-4 pt-2">
              {links.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  className="block rounded-lg px-3 py-2 text-base font-medium text-gray-700 hover:bg-gray-50"
                  onClick={() => setIsOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              <div className="mt-4 flex flex-col gap-2">
                <Link
                  href="/login"
                  className="rounded-full px-4 py-2 text-center text-sm font-medium text-dark border border-gray-200 hover:bg-gray-50"
                  onClick={() => setIsOpen(false)}
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  className="rounded-full bg-primary px-4 py-2 text-center text-sm font-medium text-primary-foreground hover:bg-primary/90"
                  onClick={() => setIsOpen(false)}
                >
                  Get Started
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}
