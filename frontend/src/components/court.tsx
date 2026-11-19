import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Line, Path, Polygon, Rect } from 'react-native-svg';

import { colors, pct, radius, space, type } from '@/lib/theme';
import type { CourtPoint, RegionResult } from '@/lib/types';

// ---- Static camera view (stands in for the live preview in the prototype) --

const W = 390;
const H = 420;
const FAR_Y = 70;
const NEAR_Y = 470; // below the frame, so the near baseline is cut off like a real phone view
const FAR = [125, 265];
const NEAR = [5, 385];

function edges(y: number): [number, number] {
  const t = (y - FAR_Y) / (NEAR_Y - FAR_Y);
  return [FAR[0] + (NEAR[0] - FAR[0]) * t, FAR[1] + (NEAR[1] - FAR[1]) * t];
}

function hLine(y: number, key: string, width = 2.5) {
  const [l, r] = edges(y);
  return <Line key={key} x1={l} y1={y} x2={r} y2={y} stroke={colors.courtLine} strokeWidth={width} />;
}

export type PlayerFrame = 'ok' | 'bad' | 'none';

/** Perspective court as seen from a tripod behind the baseline (Figma 2.2-2.5). */
export function CameraCourt({ frame = 'none', showBall = false }: { frame?: PlayerFrame; showBall?: boolean }) {
  const [nl, nr] = edges(H);
  const playerX = frame === 'bad' ? 335 : 195;
  const playerY = 345;
  const boxColor = frame === 'bad' ? colors.danger : '#3BD47E';
  return (
    <Svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice">
      <Rect x={0} y={0} width={W} height={H} fill="#1C2A22" />
      <Polygon points={`${FAR[0]},${FAR_Y} ${FAR[1]},${FAR_Y} ${nr},${H} ${nl},${H}`} fill={colors.courtFill} />
      {/* sidelines */}
      <Line x1={FAR[0]} y1={FAR_Y} x2={nl} y2={H} stroke={colors.courtLine} strokeWidth={2.5} />
      <Line x1={FAR[1]} y1={FAR_Y} x2={nr} y2={H} stroke={colors.courtLine} strokeWidth={2.5} />
      {hLine(FAR_Y, 'far-base')}
      {hLine(155, 'far-kitchen')}
      {hLine(250, 'near-kitchen')}
      {/* center service lines (not through the kitchen) */}
      <Line x1={195} y1={FAR_Y} x2={195} y2={155} stroke={colors.courtLine} strokeWidth={2} />
      <Line x1={195} y1={250} x2={195} y2={H} stroke={colors.courtLine} strokeWidth={2} />
      {/* net */}
      <Rect x={edges(190)[0] - 8} y={182} width={edges(190)[1] - edges(190)[0] + 16} height={16} fill="#0E1620" opacity={0.75} />
      <Line x1={edges(182)[0] - 8} y1={182} x2={edges(182)[1] + 8} y2={182} stroke="#E8E8E8" strokeWidth={2} />
      {showBall && (
        <>
          <Path d={`M 250 120 Q 300 230 ${playerX + 20} ${playerY - 40}`} stroke={colors.accent} strokeWidth={2} strokeDasharray="4 5" fill="none" />
          <Circle cx={250} cy={120} r={6} fill={colors.accent} />
        </>
      )}
      {frame !== 'none' && (
        <>
          {/* player figure */}
          <Circle cx={playerX} cy={playerY - 40} r={13} fill="#E8C9A4" />
          <Rect x={playerX - 16} y={playerY - 26} width={32} height={58} rx={12} fill="#EFE9E1" />
          <Rect x={playerX + 18} y={playerY - 30} width={7} height={26} rx={3} fill={colors.accent} transform={`rotate(25 ${playerX + 21} ${playerY - 17})`} />
          <Rect
            x={playerX - 30}
            y={playerY - 62}
            width={60}
            height={104}
            fill="none"
            stroke={boxColor}
            strokeWidth={2}
            strokeDasharray={frame === 'bad' ? '6 4' : undefined}
            rx={4}
          />
        </>
      )}
    </Svg>
  );
}

// ---- Coverage results (top-down) ------------------------------------------

function cellColor(r: RegionResult): string {
  if (!r.sufficient || r.success_rate == null) return colors.insufficient;
  if (r.success_rate >= 0.75) return '#3DA87A';
  if (r.success_rate >= 0.6) return '#93CDB0';
  return '#DDB97A';
}

/**
 * Return success per tested direction. Insufficient-data regions are drawn
 * gray and labelled, never as a low score (FR-12).
 */
export function CoverageCourt({ regions, minScored }: { regions: RegionResult[]; minScored: number }) {
  return (
    <View>
      <View style={styles.netRow}>
        <Text style={[type.small, { fontWeight: '600', color: colors.text }]}>Return success by direction</Text>
        <Text style={type.small}>Net ↑</Text>
      </View>
      <View style={styles.net} />
      <View style={styles.cells}>
        {regions.map((r) => (
          <View
            key={r.region_id}
            style={[styles.cell, { backgroundColor: cellColor(r) }]}
            accessibilityLabel={
              r.sufficient
                ? `${r.label}: ${pct(r.success_rate)} from ${r.scored} attempts`
                : `${r.label}: not enough data, ${r.scored} of ${minScored} attempts`
            }
          >
            <Text style={styles.cellLabel}>{r.label}</Text>
            {r.sufficient ? (
              <>
                <Text style={styles.cellValue}>{pct(r.success_rate)}</Text>
                <Text style={styles.cellMeta}>
                  {r.successes}/{r.scored} · {pct(r.ci_low)}-{pct(r.ci_high)}
                </Text>
              </>
            ) : (
              <>
                <Text style={[styles.cellValue, { fontSize: 15, color: colors.muted }]}>Not enough data</Text>
                <Text style={styles.cellMeta}>
                  {r.scored} of {minScored} needed
                </Text>
              </>
            )}
          </View>
        ))}
      </View>
      <Text style={[type.small, { marginTop: space.sm, fontSize: 12 }]}>
        Returns / scored attempts · 95% range. Seen from behind your baseline.
      </Text>
    </View>
  );
}

// ---- Tracked positions (top-down, near half) -------------------------------

// Court feet as in the harness: x 0-20 left to right as seen from behind the
// baseline, y 22 (net) to 44 (near baseline). The view adds a 2 ft margin so
// out-of-court points near the lines stay visible.
const NET_Y_FT = 22;
const KITCHEN_Y_FT = 29;
const TRANSITION_Y_FT = 36.5; // no painted line; the harness's zone boundary
const BASELINE_Y_FT = 44;
const COURT_W_FT = 20;
const MARGIN_FT = 2;
const PX_PER_FT = 14;
const VIEW_W = (COURT_W_FT + 2 * MARGIN_FT) * PX_PER_FT;
const VIEW_H = (BASELINE_Y_FT - NET_Y_FT + 2 * MARGIN_FT) * PX_PER_FT;

const sx = (xFt: number) => (xFt + MARGIN_FT) * PX_PER_FT;
const sy = (yFt: number) => (yFt - NET_Y_FT + MARGIN_FT) * PX_PER_FT;
const inView = (p: CourtPoint) =>
  p.x_ft! >= -MARGIN_FT &&
  p.x_ft! <= COURT_W_FT + MARGIN_FT &&
  p.y_ft! >= NET_Y_FT - MARGIN_FT &&
  p.y_ft! <= BASELINE_Y_FT + MARGIN_FT;

/** Interpolate from a light to a dark blue so the path reads first-to-last. */
function timeColor(t: number): string {
  const from = [0xa9, 0xc2, 0xf5];
  const to = [0x10, 0x2a, 0x8c];
  const c = from.map((f, i) => Math.round(f + (to[i] - f) * t));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

/**
 * The player's position in each sampled frame, in court feet, on the near half.
 * Frames without a position are counted, never drawn or interpolated, and
 * points outside the view are counted rather than clamped to its edge.
 */
export function TrackCourt({ points }: { points: CourtPoint[] }) {
  const located = points.filter((p) => p.x_ft != null && p.y_ft != null);
  const shown = located.filter(inView);
  const missing = points.length - located.length;
  const outsideView = located.length - shown.length;
  const last = Math.max(1, points.length - 1);
  // Join only consecutive frames; a gap (missing or off-view frame) stays a gap.
  const segments = shown
    .slice(1)
    .map((p, i) => [shown[i], p] as const)
    .filter(([a, b]) => b.frame_index === a.frame_index + 1);
  const kitchenL = sx(0);
  const kitchenR = sx(COURT_W_FT);
  return (
    <View>
      <View style={styles.netRow}>
        <Text style={[type.small, { fontWeight: '600', color: colors.text }]}>Player position per frame</Text>
        <Text style={type.small}>Net ↑</Text>
      </View>
      <Svg width="100%" viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} style={{ aspectRatio: VIEW_W / VIEW_H }}>
        <Rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill={colors.border} rx={6} />
        <Rect
          x={sx(0)}
          y={sy(NET_Y_FT)}
          width={COURT_W_FT * PX_PER_FT}
          height={(BASELINE_Y_FT - NET_Y_FT) * PX_PER_FT}
          fill={colors.courtFill}
          stroke={colors.courtLine}
          strokeWidth={2}
        />
        <Line x1={kitchenL} y1={sy(KITCHEN_Y_FT)} x2={kitchenR} y2={sy(KITCHEN_Y_FT)} stroke={colors.courtLine} strokeWidth={2} />
        <Line
          x1={sx(COURT_W_FT / 2)}
          y1={sy(KITCHEN_Y_FT)}
          x2={sx(COURT_W_FT / 2)}
          y2={sy(BASELINE_Y_FT)}
          stroke={colors.courtLine}
          strokeWidth={2}
        />
        <Line
          x1={kitchenL}
          y1={sy(TRANSITION_Y_FT)}
          x2={kitchenR}
          y2={sy(TRANSITION_Y_FT)}
          stroke={colors.courtLine}
          strokeWidth={1}
          strokeDasharray="4 4"
          opacity={0.6}
        />
        <Rect x={sx(0) - 4} y={sy(NET_Y_FT) - 3} width={COURT_W_FT * PX_PER_FT + 8} height={5} fill={colors.text} />
        {segments.map(([a, b]) => (
          <Line
            key={`seg-${b.frame_index}`}
            x1={sx(a.x_ft!)}
            y1={sy(a.y_ft!)}
            x2={sx(b.x_ft!)}
            y2={sy(b.y_ft!)}
            stroke={colors.accent}
            strokeWidth={1.5}
            opacity={0.7}
          />
        ))}
        {shown.map((p) => {
          const fill = timeColor(p.frame_index / last);
          const out = p.zone === 'out_of_court';
          return (
            <Circle
              key={`pt-${p.frame_index}`}
              cx={sx(p.x_ft!)}
              cy={sy(p.y_ft!)}
              r={5}
              fill={out ? colors.card : fill}
              stroke={out ? colors.danger : colors.card}
              strokeWidth={out ? 2 : 1}
            />
          );
        })}
      </Svg>
      <View style={styles.legend}>
        <View style={[styles.swatch, { backgroundColor: timeColor(0) }]} />
        <Text style={type.small}>first</Text>
        <View style={[styles.swatch, { backgroundColor: timeColor(1) }]} />
        <Text style={type.small}>last</Text>
        <View style={[styles.swatch, { backgroundColor: colors.card, borderColor: colors.danger, borderWidth: 2 }]} />
        <Text style={type.small}>out of court</Text>
      </View>
      <Text style={[type.small, { marginTop: 4, fontSize: 12 }]}>
        {located.length} of {points.length} frames have a position
        {missing ? ` · ${missing} without one (not drawn)` : ''}
        {outsideView ? ` · ${outsideView} outside this view (not drawn)` : ''}. Dashed line: the unpainted
        transition/backcourt boundary.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  legend: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: space.sm, flexWrap: 'wrap' },
  swatch: { width: 12, height: 12, borderRadius: 6 },
  netRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  net: { height: 3, backgroundColor: colors.text, borderRadius: 2, marginBottom: space.sm },
  cells: { flexDirection: 'row', gap: 6 },
  cell: { flex: 1, borderRadius: radius.sm, paddingVertical: space.lg, paddingHorizontal: 6, alignItems: 'center', minHeight: 120, justifyContent: 'center' },
  cellLabel: { fontSize: 12, fontWeight: '600', color: colors.text, marginBottom: 4, textAlign: 'center' },
  cellValue: { fontSize: 24, fontWeight: '700', color: colors.text, textAlign: 'center' },
  cellMeta: { fontSize: 11, color: colors.text, opacity: 0.75, marginTop: 4, textAlign: 'center' },
});
