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

module.exports = { gradeColor, formatDate, resolveMapView, GRADE_COLOR, UNION_SQUARE };
