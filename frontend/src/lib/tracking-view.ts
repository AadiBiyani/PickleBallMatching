import type { CourtPoint } from './types';

/** Match the image's aspect ratio; never use CSS pixels as original-video pixels. */
export function imagePoint(x: number, y: number, displayWidth: number, imageWidth: number, imageHeight: number): [number, number] {
  return [Math.max(0, Math.min(imageWidth, x / displayWidth * imageWidth)),
    Math.max(0, Math.min(imageHeight, y / displayWidth * imageWidth))];
}

/** A missing point breaks the trail. Never bridge a detection gap. */
export function trailSegments(rows: CourtPoint[], player: string, sourceFrame: number): [number, number][][] {
  const segments: [number, number][][] = [];
  let segment: [number, number][] = [];
  for (const row of rows.filter((r) => r.player_id === player && r.source_frame_index !== null && r.source_frame_index <= sourceFrame)) {
    if (row.x_ft === null || row.y_ft === null) {
      if (segment.length) segments.push(segment);
      segment = [];
    } else segment.push([row.x_ft, row.y_ft]);
  }
  if (segment.length) segments.push(segment);
  return segments;
}
