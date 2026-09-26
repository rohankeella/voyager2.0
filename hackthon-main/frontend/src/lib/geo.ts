/**
 * Geo helpers for the DTO-P3 3D globe.
 *
 * `greatCircle` returns spherical-interpolated waypoints between two [lng, lat]
 * pairs so the map draws a curved arc (not a Mercator straight line) on the
 * globe projection. Also handles anti-meridian crossing by unwrapping longitudes.
 */

export type LngLat = [number, number];

/**
 * Interpolate a great-circle path between two points. Returns `steps + 1`
 * coordinates including both endpoints. Longitudes are unwrapped so the
 * resulting LineString doesn't shoot across the Pacific when the shorter
 * path crosses the anti-meridian.
 */
export function greatCircle(from: LngLat, to: LngLat, steps = 64): LngLat[] {
  const rad = (d: number) => (d * Math.PI) / 180;
  const deg = (r: number) => (r * 180) / Math.PI;

  const [lng1, lat1] = from;
  const [lng2, lat2] = to;
  const phi1 = rad(lat1);
  const lam1 = rad(lng1);
  const phi2 = rad(lat2);
  const lam2 = rad(lng2);

  const dPhi = phi2 - phi1;
  const dLam = lam2 - lam1;
  const a = Math.sin(dPhi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLam / 2) ** 2;
  const d = 2 * Math.asin(Math.min(1, Math.sqrt(a)));

  if (d < 1e-9) return [from, to];

  const pts: LngLat[] = [];
  let prevLng = lng1;
  for (let i = 0; i <= steps; i++) {
    const f = i / steps;
    const A = Math.sin((1 - f) * d) / Math.sin(d);
    const B = Math.sin(f * d) / Math.sin(d);
    const x = A * Math.cos(phi1) * Math.cos(lam1) + B * Math.cos(phi2) * Math.cos(lam2);
    const y = A * Math.cos(phi1) * Math.sin(lam1) + B * Math.cos(phi2) * Math.sin(lam2);
    const z = A * Math.sin(phi1) + B * Math.sin(phi2);
    const phi = Math.atan2(z, Math.sqrt(x * x + y * y));
    let lam = deg(Math.atan2(y, x));

    // Unwrap longitude so segments don't jump 360° at anti-meridian.
    while (lam - prevLng > 180) lam -= 360;
    while (lam - prevLng < -180) lam += 360;
    prevLng = lam;

    pts.push([lam, deg(phi)]);
  }
  return pts;
}

/**
 * Bounding box across a list of coordinates. Includes safety padding so a
 * single-point trip still zooms to something reasonable.
 */
export function boundsFor(coords: LngLat[], padDeg = 5): [[number, number], [number, number]] {
  if (coords.length === 0) return [[-180, -60], [180, 75]];
  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;
  for (const [lng, lat] of coords) {
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }
  return [
    [minLng - padDeg, Math.max(-85, minLat - padDeg)],
    [maxLng + padDeg, Math.min(85, maxLat + padDeg)],
  ];
}

/**
 * Resolve the MapLibre style URL. Prefers MapTiler if a key is set (prettier,
 * proper vector tiles) else falls back to OpenFreeMap (fully free, no signup).
 */
export function resolveMapStyle(): string {
  const key = process.env.NEXT_PUBLIC_MAPTILER_KEY?.trim();
  if (key) {
    return `https://api.maptiler.com/maps/streets-v2/style.json?key=${encodeURIComponent(key)}`;
  }
  return "https://tiles.openfreemap.org/styles/liberty";
}

/**
 * Decode a Google-encoded polyline into [lng, lat] pairs.
 * Reference: https://developers.google.com/maps/documentation/utilities/polylinealgorithm
 * OpenTripPlanner emits its `legGeometry.points` in this exact format at
 * precision 5 (10^5 scaling).
 */
export function decodePolyline(encoded: string, precision = 5): LngLat[] {
  if (!encoded) return [];
  const factor = Math.pow(10, precision);
  const coords: LngLat[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;
  const len = encoded.length;

  while (index < len) {
    let result = 0;
    let shift = 0;
    let byte: number;
    do {
      if (index >= len) return coords;
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lat += (result & 1) ? ~(result >> 1) : (result >> 1);

    result = 0;
    shift = 0;
    do {
      if (index >= len) return coords;
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lng += (result & 1) ? ~(result >> 1) : (result >> 1);

    coords.push([lng / factor, lat / factor]);
  }
  return coords;
}

/**
 * OTP puts one encoded polyline per leg, joined with `|` and prefixed with
 * `MODE:`. Returns each leg separately so the renderer can style walking
 * differently from rail, etc.
 */
export type TransitLeg = { mode: string; coords: LngLat[] };

export function decodeTransitGeometry(routeGeometry: string | null | undefined): TransitLeg[] {
  if (!routeGeometry) return [];
  return routeGeometry.split("|").map((chunk) => {
    const idx = chunk.indexOf(":");
    if (idx <= 0) return { mode: "WALK", coords: decodePolyline(chunk) };
    return { mode: chunk.slice(0, idx).toUpperCase(), coords: decodePolyline(chunk.slice(idx + 1)) };
  }).filter((leg) => leg.coords.length > 1);
}
