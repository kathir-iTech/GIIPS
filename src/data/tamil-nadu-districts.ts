export interface DistrictFeature {
  type: 'Feature';
  properties: {
    name: string;
    district: string;
  };
  geometry: {
    type: 'Polygon';
    coordinates: number[][][];
  };
}

export interface DistrictsGeoJSON {
  type: 'FeatureCollection';
  features: DistrictFeature[];
}

const districts: { name: string; bounds: [number, number, number, number] }[] = [
  { name: 'Chennai', bounds: [80.10, 12.95, 80.42, 13.22] },
  { name: 'Kanchipuram', bounds: [79.50, 12.65, 79.92, 13.05] },
  { name: 'Vellore', bounds: [78.88, 12.70, 79.32, 13.12] },
  { name: 'Tiruvannamalai', bounds: [78.85, 12.05, 79.28, 12.48] },
  { name: 'Villupuram', bounds: [79.28, 11.75, 79.72, 12.18] },
  { name: 'Cuddalore', bounds: [79.52, 11.55, 79.96, 11.98] },
  { name: 'Krishnagiri', bounds: [77.88, 12.00, 78.32, 12.52] },
  { name: 'Dharmapuri', bounds: [77.88, 11.55, 78.32, 12.02] },
  { name: 'Salem', bounds: [77.88, 11.38, 78.35, 11.92] },
  { name: 'Namakkal', bounds: [77.92, 11.00, 78.38, 11.48] },
  { name: 'Erode', bounds: [77.48, 11.08, 77.92, 11.58] },
  { name: 'Tiruppur', bounds: [77.08, 10.88, 77.58, 11.32] },
  { name: 'Coimbatore', bounds: [76.68, 10.78, 77.22, 11.28] },
  { name: 'Perambalur', bounds: [78.62, 11.00, 79.08, 11.48] },
  { name: 'Ariyalur', bounds: [78.82, 10.92, 79.28, 11.38] },
  { name: 'Karur', bounds: [77.82, 10.72, 78.28, 11.18] },
  { name: 'Tiruchirappalli', bounds: [78.42, 10.52, 78.92, 11.08] },
  { name: 'Thanjavur', bounds: [78.88, 10.52, 79.38, 11.08] },
  { name: 'Mayiladuthurai', bounds: [79.38, 10.88, 79.82, 11.32] },
  { name: 'Thiruvarur', bounds: [79.38, 10.48, 79.88, 10.98] },
  { name: 'Nagapattinam', bounds: [79.58, 10.52, 80.05, 10.98] },
  { name: 'Pudukkottai', bounds: [78.52, 10.12, 79.08, 10.62] },
  { name: 'Dindigul', bounds: [77.68, 10.08, 78.28, 10.62] },
  { name: 'Madurai', bounds: [77.82, 9.68, 78.38, 10.18] },
  { name: 'Theni', bounds: [77.18, 9.78, 77.72, 10.22] },
  { name: 'Sivaganga', bounds: [78.18, 9.62, 78.72, 10.08] },
  { name: 'Virudhunagar', bounds: [77.68, 9.32, 78.22, 9.82] },
  { name: 'Ramanathapuram', bounds: [78.52, 9.12, 79.12, 9.62] },
  { name: 'Thoothukudi', bounds: [77.82, 8.48, 78.38, 9.02] },
  { name: 'Tirunelveli', bounds: [77.48, 8.42, 78.02, 8.98] },
  { name: 'Kanyakumari', bounds: [77.28, 7.82, 77.78, 8.38] },
];

function makePolygon(west: number, south: number, east: number, north: number): number[][] {
  return [
    [west, south],
    [east, south],
    [east, north],
    [west, north],
    [west, south],
  ];
}

export const tamilNaduDistricts: DistrictsGeoJSON = {
  type: 'FeatureCollection',
  features: districts.map(d => ({
    type: 'Feature' as const,
    properties: {
      name: d.name,
      district: d.name,
    },
    geometry: {
      type: 'Polygon' as const,
      coordinates: [makePolygon(d.bounds[0], d.bounds[1], d.bounds[2], d.bounds[3])],
    },
  })),
};

export const districtCentroids: Record<string, [number, number]> = {};
districts.forEach(d => {
  districtCentroids[d.name] = [
    (d.bounds[1] + d.bounds[3]) / 2,
    (d.bounds[0] + d.bounds[2]) / 2,
  ];
});
