"use client";

/**
 * DTO-P3 Phase 3 — 3D globe rendering of the SuperTrip DAG.
 *
 * Renders:
 *   • Flight edges as curved great-circle arcs (sky blue, dashed)
 *   • Ground transfer edges as straight polylines (slate, thin)
 *   • Hotel/activity/meal nodes as coloured markers
 *   • Airport nodes as filled circles anchored to flight endpoints
 *
 * Uses MapLibre GL v6's `projection: 'globe'` for a real sphere. Free
 * OpenFreeMap tiles by default; MapTiler if NEXT_PUBLIC_MAPTILER_KEY is set.
 *
 * The parent controls the highlighted node via `focusNodeId` — we call
 * `flyTo` when it changes so hovering the preview pane pans the globe.
 */

import { useCallback, useEffect, useImperativeHandle, useRef, forwardRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, LngLatBoundsLike, Map as MLMap, ProjectionSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Feature, FeatureCollection, LineString, Point } from "geojson";
import type { SuperTrip, TripNode } from "@/lib/api";
import { boundsFor, decodeTransitGeometry, greatCircle, resolveMapStyle, type LngLat } from "@/lib/geo";

type Props = {
  trip: SuperTrip;
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

const SuperTripGlobe = forwardRef<SuperTripGlobeHandle, Props>(function SuperTripGlobe(
  { trip, focusNodeId, onNodeClick },
  ref,
) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const styleReadyRef = useRef(false);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  useImperativeHandle(
    ref,
    (): SuperTripGlobeHandle => ({
      flyTo: (lng, lat, zoom = 4.5) => {
        mapRef.current?.flyTo({ center: [lng, lat], zoom, essential: true, duration: 1400 });
      },
    }),
    [],
  );

  const applyFeatures = useCallback(() => {
    const map = mapRef.current;
    if (!map || !styleReadyRef.current) return;

    const { arcs, ground, nodes, fitCoords } = buildFeatures(trip);

    (map.getSource(SRC_ARCS) as GeoJSONSource | undefined)?.setData(arcs);
    (map.getSource(SRC_GROUND) as GeoJSONSource | undefined)?.setData(ground);
    (map.getSource(SRC_NODES) as GeoJSONSource | undefined)?.setData(nodes);

    if (fitCoords.length > 0) {
      const b = boundsFor(fitCoords, 8);
      map.fitBounds(b as LngLatBoundsLike, { padding: 60, duration: 1200, maxZoom: 6 });
    }
  }, [trip]);

  // Mount the map once.
  useEffect(() => {
    if (!container.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: container.current,
      style: resolveMapStyle(),
      center: [77.59, 12.97], // Bangalore, default view
      zoom: 1.5,
      pitch: 0,
      bearing: 0,
      // MapLibre v5+ supports true globe projection.
      projection: { type: "globe" } as unknown as ProjectionSpecification,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    mapRef.current = map;

    map.on("load", () => {
      styleReadyRef.current = true;
      // set atmospheric sky on the globe when supported (skipped if style overrides)
      try {
        (map as unknown as { setSky: (s: unknown) => void }).setSky?.({
          "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 0],
        });
      } catch {
        /* older MapLibre — noop */
      }

      // Sources — start empty; applyFeatures will fill.
      const empty: FeatureCollection = { type: "FeatureCollection", features: [] };
      map.addSource(SRC_ARCS, { type: "geojson", data: empty, lineMetrics: true });
      map.addSource(SRC_GROUND, { type: "geojson", data: empty });
      map.addSource(SRC_NODES, { type: "geojson", data: empty });

      // Ground transfer layer — thin slate line, drawn under arcs so arcs pop.
      map.addLayer({
        id: "supertrip-ground-line",
        type: "line",
        source: SRC_GROUND,
        paint: {
          "line-color": "#64748b",
          "line-width": 2,
          "line-opacity": 0.8,
          "line-dasharray": [3, 2],
        },
      });

      // Flight arc glow (wide translucent)
      map.addLayer({
        id: "supertrip-arc-glow",
        type: "line",
        source: SRC_ARCS,
        paint: {
          "line-color": "#38bdf8",
          "line-width": 6,
          "line-opacity": 0.25,
          "line-blur": 3,
        },
      });

      // Flight arc solid
      map.addLayer({
        id: "supertrip-arc-line",
        type: "line",
        source: SRC_ARCS,
        paint: {
          "line-color": "#0ea5e9",
          "line-width": 2.5,
          "line-opacity": 0.9,
        },
      });

      // Node markers — coloured by category
      map.addLayer({
        id: "supertrip-node-halo",
        type: "circle",
        source: SRC_NODES,
        paint: {
          "circle-radius": 10,
          "circle-color": "#ffffff",
          "circle-opacity": 0.6,
          "circle-stroke-color": [
            "match",
            ["get", "category"],
            "hotel", "#f59e0b",
            "activity", "#10b981",
            "meal", "#e11d48",
            "guide", "#6366f1",
            "flight", "#0ea5e9",
            "transfer", "#64748b",
            /* default */ "#9ca3af",
          ],
          "circle-stroke-width": 1.5,
        },
      });

      map.addLayer({
        id: "supertrip-node-dot",
        type: "circle",
        source: SRC_NODES,
        paint: {
          "circle-radius": 5,
          "circle-color": [
            "match",
            ["get", "category"],
            "hotel", "#f59e0b",
            "activity", "#10b981",
            "meal", "#e11d48",
            "guide", "#6366f1",
            "flight", "#0ea5e9",
            "transfer", "#64748b",
            /* default */ "#9ca3af",
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5,
        },
      });

      // Interactions
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
        const p = f.properties as { title?: string; location_label?: string; cost_usd?: number; category?: string };
        popupRef.current?.remove();
        popupRef.current = new maplibregl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 12,
          className: "supertrip-popup",
        })
          .setLngLat(g.coordinates as [number, number])
          .setHTML(
            `<div style="font-family:system-ui;font-size:12px;line-height:1.35">
              <div style="font-weight:600;color:#111">${escapeHtml(p.title ?? "")}</div>
              <div style="color:#6b7280">${escapeHtml(p.location_label ?? "")}</div>
              ${typeof p.cost_usd === "number" ? `<div style="color:#0ea5e9;font-weight:600">$${p.cost_usd.toFixed(0)}</div>` : ""}
            </div>`,
          )
          .addTo(map);
      });
      map.on("click", "supertrip-node-dot", (e) => {
        const f = e.features?.[0];
        const props = f?.properties as { node_id?: string } | undefined;
        if (props?.node_id) onNodeClick?.(props.node_id);
      });

      // First paint
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

  // Fly to focused node when parent changes it.
  useEffect(() => {
    if (!focusNodeId || !mapRef.current || !styleReadyRef.current) return;
    const node = trip.nodes.find((n) => n.node_id === focusNodeId);
    const coord = node ? nodeCoord(node) || (edgeCoords(node)?.to ?? null) : null;
    if (coord) {
      mapRef.current.flyTo({ center: coord, zoom: 5.5, essential: true, duration: 1200 });
    }
  }, [focusNodeId, trip]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-3xl border border-gray-100 bg-slate-950 shadow-sm">
      <div ref={container} className="absolute inset-0" />
      <div className="pointer-events-none absolute left-3 top-3 rounded-lg bg-black/40 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white/90 backdrop-blur">
        SuperTrip · {trip.super_trip_id}
      </div>
      <div className="pointer-events-none absolute bottom-3 left-3 flex gap-3 rounded-lg bg-black/40 px-3 py-1.5 text-[10px] text-white/90 backdrop-blur">
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-sky-400" />Flights</span>
        <span className="flex items-center gap-1"><span className="h-1 w-3 rounded bg-slate-400" style={{ borderTop: "1px dashed" }} />Ground</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-400" />Hotels</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-400" />Activities</span>
      </div>
    </div>
  );
});

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export default SuperTripGlobe;
