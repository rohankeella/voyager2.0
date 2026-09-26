"use client";

/**
 * DTO-P3 Phase 3 — 3D globe rendering of the SuperTrip DAG.
 *
 * Flights draw as great-circle arcs, ground transfers as dashed polylines, and
 * hotels/activities/meals as category-coloured markers on a MapLibre globe.
 * With no trip it idles on the empty globe so the stage is never a blank box.
 * The parent controls the highlighted node via `focusNodeId`.
 */

import { useCallback, useEffect, useImperativeHandle, useRef, forwardRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { ExpressionSpecification, GeoJSONSource, LngLatBoundsLike, Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Feature, FeatureCollection, LineString, Point } from "geojson";
import { Maximize2, Minus, Plus } from "lucide-react";
import type { SuperTrip, TripNode } from "@/lib/api";
import { boundsFor, decodeTransitGeometry, greatCircle, resolveMapStyle, type LngLat } from "@/lib/geo";

// Next.js cannot infer the worker's sibling module from the bundled library URL.
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

type Props = {
  trip: SuperTrip | null;
  planning?: boolean;
  focusNodeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
};

export type SuperTripGlobeHandle = {
  flyTo: (lng: number, lat: number, zoom?: number) => void;
};

const SRC_ARCS = "supertrip-arcs";
const SRC_GROUND = "supertrip-ground";
const SRC_NODES = "supertrip-nodes";

type NodeCategory = "flight" | "hotel" | "activity" | "meal" | "guide" | "transfer" | "other";

function categorize(node: TripNode): NodeCategory {
  switch (node.type) {
    case "amadeus_flight_order":
    case "amadeus_flight_offer":
      return "flight";
    case "amadeus_hotel_booking":
    case "amadeus_hotel_offer":
      return "hotel";
    case "otp_ground_transfer":
      return "transfer";
    case "activity":
      return "activity";
    case "meal":
      return "meal";
    case "guide_session":
      return "guide";
    default:
      return "other";
  }
}

function nodeCoord(node: TripNode): LngLat | null {
  const lng = node.execution_data.lng;
  const lat = node.execution_data.lat;
  if (typeof lng === "number" && typeof lat === "number") return [lng, lat];
  return null;
}

function edgeCoords(node: TripNode): { from: LngLat; to: LngLat } | null {
  const d = node.execution_data as Record<string, unknown>;
  const oLng = d.origin_lng as number | undefined;
  const oLat = d.origin_lat as number | undefined;
  const dLng = d.destination_lng as number | undefined;
  const dLat = d.destination_lat as number | undefined;
  if (
    typeof oLng === "number" &&
    typeof oLat === "number" &&
    typeof dLng === "number" &&
    typeof dLat === "number"
  ) {
    return { from: [oLng, oLat], to: [dLng, dLat] };
  }
  return null;
}

function buildFeatures(trip: SuperTrip): {
  arcs: FeatureCollection<LineString>;
  ground: FeatureCollection<LineString>;
  nodes: FeatureCollection<Point>;
  fitCoords: LngLat[];
} {
  const arcs: Feature<LineString>[] = [];
  const ground: Feature<LineString>[] = [];
  const nodes: Feature<Point>[] = [];
  const fitCoords: LngLat[] = [];

  for (const n of trip.nodes) {
    const cat = categorize(n);
    const edge = edgeCoords(n);

    if (cat === "flight" && edge) {
      const path = greatCircle(edge.from, edge.to, 64);
      arcs.push({
        type: "Feature",
        geometry: { type: "LineString", coordinates: path },
        properties: {
          node_id: n.node_id,
          title: n.title ?? "Flight",
          cost_usd: n.financials.cost_usd,
          category: "flight",
        },
      });
      fitCoords.push(...path);
    } else if (cat === "transfer" && edge) {
      // Prefer the real OTP polyline when the Executor attached one.
      const raw = (n.execution_data as Record<string, unknown>).route_geometry;
      const transitLegs = typeof raw === "string" ? decodeTransitGeometry(raw) : [];
      if (transitLegs.length > 0) {
        for (const leg of transitLegs) {
          ground.push({
            type: "Feature",
            geometry: { type: "LineString", coordinates: leg.coords },
            properties: {
              node_id: n.node_id,
              title: `${n.title ?? "Transfer"} (${leg.mode})`,
              category: "transfer",
              mode: leg.mode,
              source: "opentripplanner",
            },
          });
          fitCoords.push(...leg.coords);
        }
      } else {
        // Fallback: straight polyline between the two endpoints.
        ground.push({
          type: "Feature",
          geometry: { type: "LineString", coordinates: [edge.from, edge.to] },
          properties: {
            node_id: n.node_id,
            title: n.title ?? "Transfer",
            category: "transfer",
            source: "haversine",
          },
        });
        fitCoords.push(edge.from, edge.to);
      }
    }

    const coord = nodeCoord(n) ?? (edge ? edge.to : null);
    if (coord) {
      nodes.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: coord },
        properties: {
          node_id: n.node_id,
          title: n.title ?? n.type,
          category: cat,
          cost_usd: n.financials.cost_usd,
          location_label: n.execution_data.location_label ?? "",
        },
      });
      fitCoords.push(coord);
    }
  }

  return {
    arcs: { type: "FeatureCollection", features: arcs },
    ground: { type: "FeatureCollection", features: ground },
    nodes: { type: "FeatureCollection", features: nodes },
    fitCoords,
  };
}

// Category colours mirror the itinerary rows (sky/amber/emerald/rose/indigo/slate),
// one step brighter so they read against the teal night globe.
const CATEGORY_COLOR: ExpressionSpecification = [
  "match",
  ["get", "category"],
  "flight", "#38bdf8",
  "hotel", "#fbbf24",
  "activity", "#34d399",
  "meal", "#fb7185",
  "guide", "#818cf8",
  "transfer", "#94a3b8",
  /* default */ "#cbd5e1",
];

const IDLE_CENTER: LngLat = [48, 22];

/** Zoom at which the whole globe spans ~70% of the pane's shorter side (radius ≈ 512·2^z / 2π px). */
function idleZoom(el: HTMLElement | null): number {
  const side = el ? Math.min(el.clientWidth, el.clientHeight) : 480;
  return Math.max(0.6, Math.log2((0.7 * side * Math.PI) / 512));
}

const LEGEND = [
  { label: "Flights", color: "bg-sky-400" },
  { label: "Hotels", color: "bg-amber-400" },
  { label: "Activities", color: "bg-emerald-400" },
  { label: "Meals", color: "bg-rose-400" },
];

function motionMs(ms: number): number {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : ms;
}

function fmtRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return "";
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${s.toLocaleDateString(undefined, opts)} – ${e.toLocaleDateString(undefined, { ...opts, year: "numeric" })}`;
}

const SuperTripGlobe = forwardRef<SuperTripGlobeHandle, Props>(function SuperTripGlobe(
  { trip, planning, focusNodeId, onNodeClick },
  ref,
) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const styleReadyRef = useRef(false);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const boundsRef = useRef<LngLatBoundsLike | null>(null);
  const onNodeClickRef = useRef(onNodeClick);
  useEffect(() => {
    onNodeClickRef.current = onNodeClick;
  }, [onNodeClick]);

  useImperativeHandle(
    ref,
    (): SuperTripGlobeHandle => ({
      flyTo: (lng, lat, zoom = 4.5) => {
        mapRef.current?.flyTo({ center: [lng, lat], zoom, essential: true, duration: motionMs(1400) });
      },
    }),
    [],
  );

  const fitRoute = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    if (boundsRef.current) {
      map.fitBounds(boundsRef.current, { padding: 72, duration: motionMs(1200), maxZoom: 5.5 });
    } else {
      map.easeTo({ center: IDLE_CENTER, zoom: idleZoom(container.current), duration: motionMs(1200) });
    }
  }, []);

  const applyFeatures = useCallback(() => {
    const map = mapRef.current;
    if (!map || !styleReadyRef.current) return;

    const empty: FeatureCollection = { type: "FeatureCollection", features: [] };
    const built = trip ? buildFeatures(trip) : null;

    (map.getSource(SRC_ARCS) as GeoJSONSource | undefined)?.setData(built?.arcs ?? empty);
    (map.getSource(SRC_GROUND) as GeoJSONSource | undefined)?.setData(built?.ground ?? empty);
    (map.getSource(SRC_NODES) as GeoJSONSource | undefined)?.setData(built?.nodes ?? empty);

    boundsRef.current =
      built && built.fitCoords.length > 0 ? (boundsFor(built.fitCoords, 6) as LngLatBoundsLike) : null;
    fitRoute();
  }, [trip, fitRoute]);

  // Mount the map once.
  useEffect(() => {
    if (!container.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: container.current,
      style: resolveMapStyle(),
      center: IDLE_CENTER,
      zoom: idleZoom(container.current),
      attributionControl: false,
    });
    mapRef.current = map;

    map.on("load", () => {
      // The local style declares the globe itself; MapTiler styles need it set.
      map.setProjection({ type: "globe" });
      styleReadyRef.current = true;

      const empty: FeatureCollection = { type: "FeatureCollection", features: [] };
      map.addSource(SRC_ARCS, { type: "geojson", data: empty, lineMetrics: true });
      map.addSource(SRC_GROUND, { type: "geojson", data: empty });
      map.addSource(SRC_NODES, { type: "geojson", data: empty });

      map.addLayer({
        id: "supertrip-ground-line",
        type: "line",
        source: SRC_GROUND,
        paint: { "line-color": "#cbd5e1", "line-width": 1.6, "line-opacity": 0.75, "line-dasharray": [2, 2] },
      });
      map.addLayer({
        id: "supertrip-arc-glow",
        type: "line",
        source: SRC_ARCS,
        layout: { "line-cap": "round" },
        paint: { "line-color": "#38bdf8", "line-width": 9, "line-opacity": 0.22, "line-blur": 5 },
      });
      map.addLayer({
        id: "supertrip-arc-line",
        type: "line",
        source: SRC_ARCS,
        layout: { "line-cap": "round" },
        paint: { "line-color": "#7dd3fc", "line-width": 2.2, "line-opacity": 0.95 },
      });
      map.addLayer({
        id: "supertrip-node-halo",
        type: "circle",
        source: SRC_NODES,
        paint: { "circle-radius": 10, "circle-color": CATEGORY_COLOR, "circle-opacity": 0.18, "circle-blur": 0.4 },
      });
      map.addLayer({
        id: "supertrip-node-dot",
        type: "circle",
        source: SRC_NODES,
        paint: {
          "circle-radius": 4.5,
          "circle-color": CATEGORY_COLOR,
          "circle-stroke-color": "#ecfeff",
          "circle-stroke-width": 1.5,
        },
      });
      map.addLayer({
        id: "supertrip-node-focus",
        type: "circle",
        source: SRC_NODES,
        filter: ["==", ["get", "node_id"], ""],
        paint: {
          "circle-radius": 11,
          "circle-opacity": 0,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });

      map.on("mouseenter", "supertrip-node-dot", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "supertrip-node-dot", () => {
        map.getCanvas().style.cursor = "";
        popupRef.current?.remove();
        popupRef.current = null;
      });
      map.on("mousemove", "supertrip-node-dot", (e) => {
        const f = e.features?.[0];
        if (!f || !f.properties) return;
        const g = f.geometry as Point;
        const p = f.properties as { title?: string; location_label?: string; cost_usd?: number };
        popupRef.current?.remove();
        popupRef.current = new maplibregl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 12,
          className: "supertrip-popup",
        })
          .setLngLat(g.coordinates as [number, number])
          .setHTML(
            `<div style="font-family:inherit;font-size:12px;line-height:1.35">
              <div style="font-weight:600;color:#0f172a">${escapeHtml(p.title ?? "")}</div>
              <div style="color:#475569">${escapeHtml(p.location_label ?? "")}</div>
              ${typeof p.cost_usd === "number" ? `<div style="color:#0f766e;font-weight:600">$${p.cost_usd.toFixed(0)}</div>` : ""}
            </div>`,
          )
          .addTo(map);
      });
      map.on("click", "supertrip-node-dot", (e) => {
        const props = e.features?.[0]?.properties as { node_id?: string } | undefined;
        if (props?.node_id) onNodeClickRef.current?.(props.node_id);
      });

      applyFeatures();
    });

    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
      styleReadyRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-render features when trip changes.
  useEffect(() => {
    applyFeatures();
  }, [applyFeatures]);

  // Highlight and fly to the node focused from the itinerary.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReadyRef.current) return;
    map.setFilter("supertrip-node-focus", ["==", ["get", "node_id"], focusNodeId ?? ""]);
    if (!focusNodeId || !trip) return;
    const node = trip.nodes.find((n) => n.node_id === focusNodeId);
    const coord = node ? nodeCoord(node) || (edgeCoords(node)?.to ?? null) : null;
    if (coord) map.flyTo({ center: coord, zoom: 5, essential: true, duration: motionMs(1200) });
  }, [focusNodeId, trip]);

  const g = trip?.global_constraints;
  const from = g?.home_location?.split(",")[0];
  const to = g?.destination?.split(",")[0];

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl bg-[radial-gradient(110%_85%_at_50%_42%,#0f3b3d_0%,#082830_42%,#031017_100%)] shadow-[0_18px_40px_-24px_rgba(4,23,26,0.7)]">
      {/* h-full, not absolute inset-0: maplibregl-map CSS forces position:relative, collapsing it to 0px */}
      <div ref={container} className="h-full w-full" role="region" aria-label="Trip route map" />

      {trip && g && (
        <div className="pointer-events-none absolute left-4 top-4 max-w-[calc(100%-6rem)] rounded-xl bg-[#031017]/70 px-3.5 py-2.5 ring-1 ring-white/10">
          <div className="truncate text-sm font-semibold text-white">
            {from && to ? (
              <>
                {from} <span className="text-teal-300">→</span> {to}
              </>
            ) : (
              to || from || "Your trip"
            )}
          </div>
          <div className="mt-0.5 text-xs tabular-nums text-teal-100/75">
            {fmtRange(g.start_date, g.end_date)} · {trip.nodes.length} stop{trip.nodes.length === 1 ? "" : "s"}
          </div>
        </div>
      )}

      <div className="absolute right-4 top-4 flex flex-col divide-y divide-white/10 overflow-hidden rounded-xl bg-[#031017]/70 ring-1 ring-white/10">
        <MapButton label="Zoom in" onClick={() => mapRef.current?.zoomIn({ duration: motionMs(300) })}>
          <Plus className="h-4 w-4" />
        </MapButton>
        <MapButton label="Zoom out" onClick={() => mapRef.current?.zoomOut({ duration: motionMs(300) })}>
          <Minus className="h-4 w-4" />
        </MapButton>
        <MapButton label={trip ? "Fit whole route" : "Reset view"} onClick={fitRoute}>
          <Maximize2 className="h-3.5 w-3.5" />
        </MapButton>
      </div>

      {trip ? (
        <ul className="pointer-events-none absolute bottom-4 left-4 flex flex-wrap gap-x-3 gap-y-1 rounded-xl bg-[#031017]/70 px-3 py-2 text-[11px] text-teal-50/85 ring-1 ring-white/10">
          {LEGEND.map((l) => (
            <li key={l.label} className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${l.color}`} />
              {l.label}
            </li>
          ))}
          <li className="flex items-center gap-1.5">
            <span className="w-3 border-t border-dashed border-slate-300" />
            Ground
          </li>
        </ul>
      ) : (
        <div className="pointer-events-none absolute inset-x-4 bottom-6 flex justify-center">
          <p className="max-w-sm rounded-xl bg-[#031017]/70 px-4 py-2.5 text-center text-xs leading-relaxed text-teal-50/85 ring-1 ring-white/10">
            {planning
              ? "Planning your route… it will be drawn here as soon as the agents finish."
              : "Describe a trip in the chat. Flights, transfers, stays and stops will be drawn on this globe."}
          </p>
        </div>
      )}
    </div>
  );
});

function MapButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="flex h-9 w-9 items-center justify-center text-teal-50/80 transition-colors duration-150 hover:bg-white/10 hover:text-white focus-visible:bg-white/15 focus-visible:text-white focus-visible:outline-none"
    >
      {children}
    </button>
  );
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export default SuperTripGlobe;
