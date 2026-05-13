// scripts/geo.js
"use strict";

/** Ray-casting point-in-polygon. GeoJSON ring format: [[lng,lat],...] */
function pointInRing(lng, lat, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if (((yi > lat) !== (yj > lat)) && lng < (xj - xi) * (lat - yi) / (yj - yi) + xi)
      inside = !inside;
  }
  return inside;
}

/** Check if [lng,lat] falls inside a GeoJSON Feature (Polygon or MultiPolygon). */
function pointInFeature(lng, lat, feature) {
  const geom = feature.geometry;
  const polys = geom.type === "MultiPolygon" ? geom.coordinates : [geom.coordinates];
  return polys.some(poly => pointInRing(lng, lat, poly[0]));
}

/**
 * Returns true if [lat,lng] is inside any feature in the features array.
 * Pass the .features array from a loaded GeoJSON FeatureCollection.
 */
function isInNYC(lat, lng, features) {
  if (!features || !features.length) return false;
  return features.some(f => pointInFeature(lng, lat, f));
}

module.exports = { pointInRing, pointInFeature, isInNYC };
