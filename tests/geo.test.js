const { pointInRing, pointInFeature, isInNYC } = require("../scripts/geo");

// Simple square polygon centred around Union Square, GeoJSON [lng,lat] order
const SQUARE = [
  [-74.0, 40.7],
  [-73.9, 40.7],
  [-73.9, 40.8],
  [-74.0, 40.8],
  [-74.0, 40.7],  // closed
];

describe("pointInRing", () => {
  test("point clearly inside returns true", () => {
    expect(pointInRing(-73.95, 40.75, SQUARE)).toBe(true);
  });
  test("point clearly outside returns false", () => {
    expect(pointInRing(-74.1, 40.75, SQUARE)).toBe(false);
  });
  test("point above the ring returns false", () => {
    expect(pointInRing(-73.95, 40.9, SQUARE)).toBe(false);
  });
  test("point below the ring returns false", () => {
    expect(pointInRing(-73.95, 40.6, SQUARE)).toBe(false);
  });
});

describe("pointInFeature", () => {
  const feature = {
    type: "Feature",
    geometry: { type: "Polygon", coordinates: [SQUARE] },
  };
  test("inside feature returns true", () => {
    expect(pointInFeature(-73.95, 40.75, feature)).toBe(true);
  });
  test("outside feature returns false", () => {
    expect(pointInFeature(-74.5, 40.75, feature)).toBe(false);
  });

  test("MultiPolygon: inside second polygon returns true", () => {
    const SQUARE2 = [
      [-73.8, 40.6], [-73.7, 40.6], [-73.7, 40.7], [-73.8, 40.7], [-73.8, 40.6],
    ];
    const multi = {
      type: "Feature",
      geometry: { type: "MultiPolygon", coordinates: [[SQUARE], [SQUARE2]] },
    };
    expect(pointInFeature(-73.75, 40.65, multi)).toBe(true);
    expect(pointInFeature(-73.95, 40.75, multi)).toBe(true);
    expect(pointInFeature(-74.5, 40.75, multi)).toBe(false);
  });
});

describe("isInNYC", () => {
  // Tiny mock GeoJSON — just a bounding box over Manhattan
  const MANHATTAN_BOX = [
    [-74.02, 40.70], [-73.97, 40.70], [-73.97, 40.78], [-74.02, 40.78], [-74.02, 40.70],
  ];
  const mockFeatures = [
    {
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [MANHATTAN_BOX] },
      properties: { boro_name: "Manhattan" },
    },
  ];

  test("Times Square (Manhattan) → true", () => {
    // 40.7580, -73.9855
    expect(isInNYC(40.7580, -73.9855, mockFeatures)).toBe(true);
  });
  test("Midtown (Manhattan) → true", () => {
    expect(isInNYC(40.754, -73.990, mockFeatures)).toBe(true);
  });
  test("Newark NJ → false", () => {
    expect(isInNYC(40.7357, -74.1724, mockFeatures)).toBe(false);
  });
  test("Hoboken NJ → false", () => {
    expect(isInNYC(40.7440, -74.0324, mockFeatures)).toBe(false);
  });
  test("empty features array → false", () => {
    expect(isInNYC(40.7580, -73.9855, [])).toBe(false);
  });
  test("null features → false", () => {
    expect(isInNYC(40.7580, -73.9855, null)).toBe(false);
  });
});
