import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Line, Path, Polygon, Rect } from 'react-native-svg';

import { colors, pct, radius, space, type } from '@/lib/theme';
import type { RegionResult } from '@/lib/types';

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

const styles = StyleSheet.create({
  netRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  net: { height: 3, backgroundColor: colors.text, borderRadius: 2, marginBottom: space.sm },
  cells: { flexDirection: 'row', gap: 6 },
  cell: { flex: 1, borderRadius: radius.sm, paddingVertical: space.lg, paddingHorizontal: 6, alignItems: 'center', minHeight: 120, justifyContent: 'center' },
  cellLabel: { fontSize: 12, fontWeight: '600', color: colors.text, marginBottom: 4, textAlign: 'center' },
  cellValue: { fontSize: 24, fontWeight: '700', color: colors.text, textAlign: 'center' },
  cellMeta: { fontSize: 11, color: colors.text, opacity: 0.75, marginTop: 4, textAlign: 'center' },
});
