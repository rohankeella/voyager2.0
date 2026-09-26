"use client";

import { useState } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  images: string[];
  alt: string;
};

export default function ImageGallery({ images, alt }: Props) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  const thumbnailImages = images.length >= 4 ? images.slice(0, 4) : [...images];
  const mainImage = images[0];

  const nextImage = () => setCurrentIndex((i) => (i + 1) % images.length);
  const prevImage = () => setCurrentIndex((i) => (i - 1 + images.length) % images.length);

  return (
    <>
      <div className="grid grid-cols-12 gap-2 sm:gap-3">
        <div className="col-span-12 sm:col-span-8 relative aspect-[4/3] rounded-2xl overflow-hidden group">
          <Image src={mainImage} alt={alt} fill sizes="(max-width: 640px) 100vw, 60vw" className="object-cover group-hover:scale-105 transition-transform duration-500" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent opacity-100 transition-opacity" />
          <button
            onClick={() => {
              setCurrentIndex(0);
              setLightboxOpen(true);
            }}
            className="absolute bottom-4 right-4 rounded-full bg-white/90 p-2 text-gray-600 opacity-0 transition-opacity group-hover:opacity-100"
            aria-label="View fullscreen"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9 9 9 0 01-9-9 9 9 0 019-9 9 9 0 019 9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l5-3-5-3v6z" />
            </svg>
          </button>
        </div>

        {thumbnailImages.slice(1).map((image, index) => {
          const colSpan = index === 0 && thumbnailImages.length === 4 ? "sm:col-span-4" : "sm:col-span-2";
          return (
            <div key={index} className={cn("col-span-4 sm:col-span-2 relative aspect-[4/3] rounded-xl overflow-hidden group cursor-zoom-in", colSpan)} onClick={() => {
              setCurrentIndex(index + 1);
              setLightboxOpen(true);
            }}>
              <Image src={image} alt={`${alt} ${index + 2}`} fill sizes="(max-width: 640px) 33vw, (max-width: 768px) 20vw" className="object-cover" />
            </div>
          );
        })}
      </div>

      <AnimatePresence>
        {lightboxOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
            onClick={() => setLightboxOpen(false)}
          >
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="relative max-w-6xl max-h-[85vh]"
              onClick={(e) => e.stopPropagation()}
            >
              <Image
                src={images[currentIndex]}
                alt={`${alt} ${currentIndex + 1}`}
                width={1200}
                height={800}
                className="rounded-xl object-contain max-w-full max-h-[85vh]"
              />
              <button
                onClick={prevImage}
                className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
                aria-label="Previous image"
              >
                <ChevronLeft className="h-6 w-6" />
              </button>
              <button
                onClick={nextImage}
                className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
                aria-label="Next image"
              >
                <ChevronRight className="h-6 w-6" />
              </button>
              <button
                onClick={() => setLightboxOpen(false)}
                className="absolute top-4 right-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
              <div className="mt-4 text-center text-sm text-gray-400">
                {currentIndex + 1} of {images.length}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
