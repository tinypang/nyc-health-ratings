const { gradeColor, formatDate, resolveMapView, resolveAutoLocate, applyPendingAutoLocate, UNION_SQUARE } = require("../scripts/utils");

describe("gradeColor", () => {
  test("A → green", () => expect(gradeColor("A")).toBe("#22c55e"));
  test("B → yellow", () => expect(gradeColor("B")).toBe("#eab308"));
  test("C → red",    () => expect(gradeColor("C")).toBe("#ef4444"));
  test("P → purple", () => expect(gradeColor("P")).toBe("#a855f7"));
  test("Z → orange", () => expect(gradeColor("Z")).toBe("#f97316"));
  test("N → grey",   () => expect(gradeColor("N")).toBe("#6b7280"));
  test("unknown grade falls back to N colour", () => {
    expect(gradeColor("X")).toBe("#6b7280");
  });
});

describe("formatDate", () => {
  test("ISO date string formats correctly", () => {
    // Use a fixed UTC offset to avoid timezone flakiness in CI
    const result = formatDate("2024-06-15T00:00:00.000Z");
    expect(result).toMatch(/Jun/);
    expect(result).toMatch(/2024/);
  });
  test("null returns em-dash", () => expect(formatDate(null)).toBe("—"));
  test("undefined returns em-dash", () => expect(formatDate(undefined)).toBe("—"));
  test("empty string returns em-dash", () => expect(formatDate("")).toBe("—"));
});

describe("resolveMapView", () => {
  // Minimal mock features: a box covering roughly Manhattan/inner NYC
  const NYC_BOX = [
    [-74.02, 40.70], [-73.97, 40.70], [-73.97, 40.78],
    [-74.02, 40.78], [-74.02, 40.70],
  ];
  const mockFeatures = [{
    type: "Feature",
    geometry: { type: "Polygon", coordinates: [NYC_BOX] },
    properties: {},
  }];

  test("user inside NYC → their location at zoom 18", () => {
    const view = resolveMapView(40.754, -73.990, mockFeatures);
    expect(view.lat).toBeCloseTo(40.754);
    expect(view.lng).toBeCloseTo(-73.990);
    expect(view.zoom).toBe(18);
  });

  test("user outside NYC (NJ) → Union Square at zoom 14", () => {
    const view = resolveMapView(40.7357, -74.1724, mockFeatures);
    expect(view.lat).toBeCloseTo(UNION_SQUARE.lat);
    expect(view.lng).toBeCloseTo(UNION_SQUARE.lng);
    expect(view.zoom).toBe(14);
  });

  test("user far outside NYC → Union Square", () => {
    const view = resolveMapView(51.5074, -0.1278, mockFeatures); // London
    expect(view.lat).toBeCloseTo(UNION_SQUARE.lat);
    expect(view.zoom).toBe(14);
  });

  test("features not yet loaded → Union Square fallback", () => {
    const view = resolveMapView(40.754, -73.990, null);
    expect(view.lat).toBeCloseTo(UNION_SQUARE.lat);
    expect(view.zoom).toBe(14);
  });
});

// Shared mock for the race condition tests below
const NYC_BOX = [
  [-74.02, 40.70], [-73.97, 40.70], [-73.97, 40.78],
  [-74.02, 40.78], [-74.02, 40.70],
];
const mockFeatures = [{
  type: "Feature",
  geometry: { type: "Polygon", coordinates: [NYC_BOX] },
  properties: {},
}];

describe("resolveAutoLocate — page-load race condition", () => {
  // These tests cover the case where getCurrentPosition (using a cached GPS fix)
  // resolves before the NYC borough GeoJSON has finished loading. Without the fix,
  // isInNYC sees null features and returns false, leaving NYC users on Union Square.

  test("GeoJSON not yet loaded → returns 'pending' so position can be stored", () => {
    expect(resolveAutoLocate(40.754, -73.990, null)).toBe("pending");
  });

  test("GeoJSON not yet loaded, outside NYC → still returns 'pending'", () => {
    // Position is stored regardless; applyPendingAutoLocate handles the NYC check later
    expect(resolveAutoLocate(40.7357, -74.1724, null)).toBe("pending");
  });

  test("GeoJSON loaded, user inside NYC → returns zoom-18 view immediately", () => {
    const view = resolveAutoLocate(40.754, -73.990, mockFeatures);
    expect(view.lat).toBeCloseTo(40.754);
    expect(view.lng).toBeCloseTo(-73.990);
    expect(view.zoom).toBe(18);
  });

  test("GeoJSON loaded, user outside NYC → returns null (stay on Union Square silently)", () => {
    expect(resolveAutoLocate(40.7357, -74.1724, mockFeatures)).toBeNull();
  });
});

describe("applyPendingAutoLocate — resolves stored position once GeoJSON loads", () => {
  // Called by loadNYCBoroughBounds after features arrive, to action any position
  // that was parked while the GeoJSON was in flight.

  test("pending NYC position → zoom-18 view applied when GeoJSON finishes", () => {
    const view = applyPendingAutoLocate(mockFeatures, { lat: 40.754, lng: -73.990 });
    expect(view.lat).toBeCloseTo(40.754);
    expect(view.lng).toBeCloseTo(-73.990);
    expect(view.zoom).toBe(18);
  });

  test("pending outside-NYC position → null (map stays on Union Square)", () => {
    expect(applyPendingAutoLocate(mockFeatures, { lat: 40.7357, lng: -74.1724 })).toBeNull();
  });

  test("no pending position → null (nothing to do)", () => {
    expect(applyPendingAutoLocate(mockFeatures, null)).toBeNull();
  });

  test("GeoJSON failed to load → null (stay on Union Square regardless of position)", () => {
    expect(applyPendingAutoLocate(null, { lat: 40.754, lng: -73.990 })).toBeNull();
  });
});
