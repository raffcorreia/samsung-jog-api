/**
 * Annulus sector path for SVG (degrees: 0 = east, 90 = south, 270 = north; y-down coords).
 * Used for circular 4-way ring segments with a hollow center.
 */
export function annulusSectorPath(
  cx: number,
  cy: number,
  rIn: number,
  rOut: number,
  startDeg: number,
  endDeg: number,
): string {
  const rad = (d: number) => (d * Math.PI) / 180;
  const x = (r: number, d: number) => cx + r * Math.cos(rad(d));
  const y = (r: number, d: number) => cy + r * Math.sin(rad(d));
  let sweep = endDeg - startDeg;
  if (sweep <= 0) {
    sweep += 360;
  }
  const large = sweep > 180 ? 1 : 0;
  return [
    `M ${x(rOut, startDeg)} ${y(rOut, startDeg)}`,
    `A ${rOut} ${rOut} 0 ${large} 1 ${x(rOut, endDeg)} ${y(rOut, endDeg)}`,
    `L ${x(rIn, endDeg)} ${y(rIn, endDeg)}`,
    `A ${rIn} ${rIn} 0 ${large} 0 ${x(rIn, startDeg)} ${y(rIn, startDeg)}`,
    "Z",
  ].join(" ");
}
