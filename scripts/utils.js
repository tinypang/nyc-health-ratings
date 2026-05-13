// scripts/utils.js
"use strict";

const GRADE_COLOR = {
  A: "#22c55e",
  B: "#eab308",
  C: "#ef4444",
  P: "#a855f7",
  Z: "#f97316",
  N: "#6b7280",
};

function gradeColor(grade) {
  return GRADE_COLOR[grade] || GRADE_COLOR.N;
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric",
  });
}

/**
 * Given a user's geolocation and the loaded NYC borough features,
 * return the map view to set: { lat, lng, zoom }.
 * - Inside NYC  → user's location at zoom 18
 * - Outside NYC → Union Square at zoom 14
 */
const UNION_SQUARE = { lat: 40.7359, lng: -73.9911, zoom: 14 };

function resolveMapView(userLat, userLng, nycFeatures) {
  const { isInNYC } = require("./geo");
  if (isInNYC(userLat, userLng, nycFeatures)) {
    return { lat: userLat, lng: userLng, zoom: 18 };
  }
  return { ...UNION_SQUARE };
}

/**
 * Determines what the page-load auto-locate should do when geolocation resolves.
 *
 * Two cases:
 *  - GeoJSON already loaded  → decide immediately; return a view or null
 *  - GeoJSON still loading   → return 'pending' so the caller can park the
 *                              position and pass it to applyPendingAutoLocate
 *                              once the features arrive
 *
 * Returns:
 *  { lat, lng, zoom: 18 }  — user is in NYC, set this view
 *  null                    — user is outside NYC, do nothing (stay on Union Square)
 *  'pending'               — features not loaded yet, store position for later
 */
function resolveAutoLocate(userLat, userLng, nycFeatures) {
  const { isInNYC } = require("./geo");
  if (nycFeatures === null || nycFeatures === undefined) {
    return "pending";
  }
  if (isInNYC(userLat, userLng, nycFeatures)) {
    return { lat: userLat, lng: userLng, zoom: 18 };
  }
  return null;
}

/**
 * Called by loadNYCBoroughBounds once features have loaded, to resolve any
 * geolocation position that arrived before the GeoJSON was ready.
 *
 * Returns:
 *  { lat, lng, zoom: 18 }  — pending position is inside NYC, set this view
 *  null                    — no pending position, outside NYC, or GeoJSON failed
 */
function applyPendingAutoLocate(nycFeatures, pendingPos) {
  const { isInNYC } = require("./geo");
  if (!pendingPos || !nycFeatures) return null;
  const { lat, lng } = pendingPos;
  if (isInNYC(lat, lng, nycFeatures)) {
    return { lat, lng, zoom: 18 };
  }
  return null;
}

module.exports = {
  gradeColor, formatDate, resolveMapView,
  resolveAutoLocate, applyPendingAutoLocate,
  GRADE_COLOR, UNION_SQUARE,
};
