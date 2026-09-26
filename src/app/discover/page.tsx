"use client";

import { useState, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Filter, Grid, List } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import DestinationCard from "@/components/destinations/destination-card";
import SearchBar from "@/components/discover/search-bar";
import FilterPanel, { type Filters } from "@/components/discover/filter-panel";
import CategoryTabs from "@/components/discover/category-tabs";
import { destinations } from "@/lib/mock-data";

const initialFilters: Filters = {
  destinationTypes: [],
  budget: [],
  season: [],
  activities: [],
  minCost: 0,
  maxCost: 500,
};

export default function DiscoverPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  useEffect(() => {
    document.body.style.overflow = showMobileFilters ? "hidden" : "";
  }, [showMobileFilters]);

  const filteredDestinations = useMemo(() => {
    let result = destinations;

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      result = result.filter(
        (d) => d.name.toLowerCase().includes(query) || d.country.toLowerCase().includes(query) || d.tags.some((t) => t.toLowerCase().includes(query))
      );
    }

    if (selectedCategory === "trending") {
      result = result.filter((d) => d.destinationTypes.includes("cities")).sort((a, b) => (b.matchScore ?? 0) - (a.matchScore ?? 0));
    } else if (selectedCategory === "beaches") {
      result = result.filter((d) => d.destinationTypes.includes("beaches"));
    } else if (selectedCategory === "mountains") {
      result = result.filter((d) => d.destinationTypes.includes("mountains"));
    } else if (selectedCategory === "cities") {
      result = result.filter((d) => d.destinationTypes.includes("cities"));
    } else if (selectedCategory === "tropical") {
      result = result.filter((d) => d.destinationTypes.includes("tropical"));
    } else if (selectedCategory === "snow") {
      result = result.filter((d) => d.destinationTypes.includes("snow"));
    } else if (selectedCategory === "budget") {
      result = result
        .filter((d) => d.budget === "backpacker" || d.budget === "budget")
        .sort((a, b) => a.estimatedDailyCost - b.estimatedDailyCost);
    } else if (selectedCategory === "luxury") {
      result = result
        .filter((d) => d.budget === "premium" || d.budget === "luxury")
        .sort((a, b) => b.estimatedDailyCost - a.estimatedDailyCost);
    } else if (selectedCategory === "hidden") {
      result = result.filter((d) => d.tags.includes("unique"));
    }

    if (filters.destinationTypes.length > 0) {
      result = result.filter((d) => d.destinationTypes.some((dt) => filters.destinationTypes.includes(dt)));
    }

    if (filters.budget.length > 0) {
      result = result.filter((d) => filters.budget.includes(d.budget));
    }

    if (filters.season.length > 0) {
      result = result.filter((d) => d.bestSeason.some((s) => filters.season.includes(s)));
    }

    if (filters.activities.length > 0) {
      result = result.filter((d) => d.activities.some((a) => filters.activities.includes(a)));
    }

    result = result.filter((d) => d.estimatedDailyCost >= filters.minCost && d.estimatedDailyCost <= filters.maxCost);

    return result;
  }, [searchQuery, selectedCategory, filters]);

  const activeFilterCount =
    filters.destinationTypes.length +
    filters.budget.length +
    filters.season.length +
    filters.activities.length +
    (filters.minCost > 0 ? 1 : 0) +
    (filters.maxCost < 500 ? 1 : 0);

  const handleResetFilters = () => {
    setFilters(initialFilters);
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <div className="mx-auto max-w-7xl px-4 pt-24 pb-10 sm:px-6 lg:px-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-bold text-dark sm:text-4xl">Discover Destinations</h1>
          <p className="mt-2 text-gray-600">Find your next adventure with our curated list of destinations</p>
        </motion.div>

        <div className="mb-6">
          <SearchBar value={searchQuery} onChange={setSearchQuery} placeholder="Search destinations, countries, or tags..." />
        </div>

        <CategoryTabs selected={selectedCategory} onSelect={setSelectedCategory} />

        <div className="mb-6 flex items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => setShowMobileFilters(true)}
              className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-dark transition-colors hover:bg-gray-50 lg:hidden"
            >
              <Filter className="h-4 w-4" />
              Filters
            </button>
            <button
              onClick={() => setShowMobileFilters(true)}
              className="hidden items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-dark transition-colors hover:bg-gray-50 lg:flex"
            >
              <Filter className="h-4 w-4" />
              Filters ({activeFilterCount})
            </button>
            <button
              onClick={() => setShowMobileFilters(true)}
              className="hidden items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-dark transition-colors hover:bg-gray-50 md:flex"
            >
              Categories
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode("grid")}
              className={`rounded-lg p-2 text-sm ${viewMode === "grid" ? "bg-primary text-primary-foreground" : "bg-white text-gray-600 hover:bg-gray-50"}`}
              aria-label="Grid view"
            >
              <Grid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`rounded-lg p-2 text-sm ${viewMode === "list" ? "bg-primary text-primary-foreground" : "bg-white text-gray-600 hover:bg-gray-50"}`}
              aria-label="List view"
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex gap-8">
          <div className="hidden w-72 flex-shrink-0 lg:block">
            <div className="sticky top-24 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-dark">Filters</h3>
                {activeFilterCount > 0 && (
                  <span className="inline-flex items-center justify-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                    {activeFilterCount}
                  </span>
                )}
              </div>
              <FilterPanel filters={filters} onChange={setFilters} onReset={handleResetFilters} activeCount={activeFilterCount} />
            </div>
          </div>

          <div className="flex-1">
            <AnimatePresence>
              {filteredDestinations.length > 0 ? (
                <motion.div
                  key={"results" + filteredDestinations.length}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className={viewMode === "grid" ? "grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" : "flex flex-col gap-4"}
                >
                  {filteredDestinations.map((destination, index) => (
                    <DestinationCard key={destination.id} destination={destination} index={index} />
                  ))}
                </motion.div>
              ) : (
                <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="py-20 text-center">
                  <p className="text-gray-500">No destinations found matching your criteria.</p>
                  <button onClick={handleResetFilters} className="mt-4 rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
                    Clear all filters
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {showMobileFilters && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 bg-black/50 lg:hidden" onClick={() => setShowMobileFilters(false)} />

            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "tween", duration: 0.3 }}
              className="fixed inset-y-0 right-0 z-50 w-full max-w-sm border-l border-gray-200 bg-white shadow-xl lg:hidden"
            >
              <div className="flex items-center justify-between border-b border-gray-100 p-4">
                <h3 className="text-lg font-semibold text-dark">Filters</h3>
                <button onClick={() => setShowMobileFilters(false)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100">
                  <Filter className="h-5 w-5" />
                </button>
              </div>

              <div className="p-6">
                <FilterPanel filters={filters} onChange={setFilters} onReset={handleResetFilters} activeCount={activeFilterCount} />
              </div>

              <div className="border-t border-gray-100 p-4">
                <button
                  onClick={() => {
                    setShowMobileFilters(false);
                  }}
                  className="flex w-full items-center justify-center rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
                >
                  Apply Filters
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
