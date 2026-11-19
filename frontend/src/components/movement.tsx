import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Line, Polyline, Rect } from 'react-native-svg';

import { colors, radius, space, type } from '@/lib/theme';
import type { CourtPoint, Results, Zone } from '@/lib/types';

// Court feet, as in the court evaluation harness: origin far-left outside corner,
// x 0-20 toward the right sideline, y 0-44 toward the near baseline, net at y = 22.
const NET_Y = 22;
const KITCHEN_Y = 29;
const TRANSITION_Y = 36.5; // no painted line; shown dashed
const BASELINE_Y = 44;
const VIEW = { x: -2, y: NET_Y - 1, w: 24, h: BASELINE_Y - NET_Y + 5 }; // near half plus a margin behind the baseline

const ZONE_LABELS: Record<Zone, string> = {
  kitchen_left: 'Kitchen left',
  kitchen_right: 'Kitchen right',
  transition_left: 'Transition left',
  transition_right: 'Transition right',
  backcourt_left: 'Backcourt left',
  backcourt_right: 'Backcourt right',
  out_of_court: 'Out of court',
  not_visible: 'Not visible',
};
const ZONE_ORDER = Object.keys(ZONE_LABELS) as Zone[];

function inView(p: CourtPoint): p is CourtPoint & { x_ft: number; y_ft: number } {
  return (
    p.x_ft != null &&
    p.y_ft != null &&
    p.x_ft >= VIEW.x &&
    p.x_ft <= VIEW.x + VIEW.w &&
    p.y_ft >= VIEW.y &&
    p.y_ft <= VIEW.y + VIEW.h
  );
}

/**
 * The tracking model's output for this session: where the player was on the
 * near half of the court, and the share of sampled frames in each harness zone.
 * Positions are real model output; attempt outcomes elsewhere are still simulated.
 */
export function MovementCard({ points, track }: { points: CourtPoint[]; track: Results['track'] }) {
  const drawn = points.filter(inView);
  const total = points.length || 1;
  const counts = track.zone_counts;
  const offView = points.filter((p) => p.x_ft != null && !inView(p)).length;
  const isSimulated = track.model_id === 'simulated';

  return (
    <View>
      <View style={styles.header}>
        <Text style={[type.small, { fontWeight: '600', color: colors.text }]}>Movement</Text>
        <Text style={type.small}>
          {isSimulated ? 'Simulated tracker' : `${track.kind} model`} · {points.length} frames at {track.sample_fps} fps
        </Text>
      </View>
      <View style={styles.court} accessibilityLabel={`Court plot of ${drawn.length} tracked positions on the near half`}>
        <Svg width="100%" height="100%" viewBox={`${VIEW.x} ${VIEW.y} ${VIEW.w} ${VIEW.h}`}>
          <Rect x={VIEW.x} y={VIEW.y} width={VIEW.w} height={VIEW.h} fill="#E9F0E7" />
          <Rect x={0} y={NET_Y} width={20} height={BASELINE_Y - NET_Y} fill={colors.courtFill} opacity={0.18} />
          <Line x1={0} y1={NET_Y} x2={0} y2={BASELINE_Y} stroke={colors.text} strokeWidth={0.12} />
          <Line x1={20} y1={NET_Y} x2={20} y2={BASELINE_Y} stroke={colors.text} strokeWidth={0.12} />
          <Line x1={0} y1={BASELINE_Y} x2={20} y2={BASELINE_Y} stroke={colors.text} strokeWidth={0.12} />
          <Line x1={0} y1={KITCHEN_Y} x2={20} y2={KITCHEN_Y} stroke={colors.text} strokeWidth={0.12} />
          <Line x1={10} y1={KITCHEN_Y} x2={10} y2={BASELINE_Y} stroke={colors.text} strokeWidth={0.12} />
          <Line x1={0} y1={TRANSITION_Y} x2={20} y2={TRANSITION_Y} stroke={colors.muted} strokeWidth={0.08} strokeDasharray="0.5 0.5" />
          <Line x1={-1} y1={NET_Y} x2={21} y2={NET_Y} stroke={colors.text} strokeWidth={0.35} />
          {drawn.length > 1 && (
            <Polyline
              points={drawn.map((p) => `${p.x_ft},${p.y_ft}`).join(' ')}
              fill="none"
              stroke={colors.primary}
              strokeWidth={0.08}
              opacity={0.35}
            />
          )}
          {drawn.map((p, i) => (
            <Circle
              key={p.frame_index}
              cx={p.x_ft}
              cy={p.y_ft}
              r={0.28}
              fill={colors.primary}
              opacity={0.35 + 0.65 * (i / Math.max(1, drawn.length - 1))}
            />
          ))}
        </Svg>
        <Text style={styles.net}>Net</Text>
        {drawn.length === 0 && (
          <View style={styles.empty}>
            <Text style={[type.small, { color: colors.text, textAlign: 'center' }]}>
              {points.length > 0 && track.missing_frames === points.length
                ? 'The model did not find the player in any sampled frame.'
                : 'No positions fall on the near half of the court.'}
            </Text>
          </View>
        )}
      </View>
      <Text style={[type.small, { fontSize: 11, marginTop: 4 }]}>
        Darker dots are later in the clip.
        {offView > 0 ? ` ${offView} positions fall outside this view (far half or well off court).` : ''}
      </Text>

      <View style={{ marginTop: space.md, gap: 6 }}>
        {ZONE_ORDER.filter((z) => counts[z]).map((z) => {
          const share = (counts[z] ?? 0) / total;
          return (
            <View key={z} style={styles.zoneRow} accessibilityLabel={`${ZONE_LABELS[z]}: ${Math.round(share * 100)}%`}>
              <Text style={[type.small, styles.zoneLabel]}>{ZONE_LABELS[z]}</Text>
              <View style={styles.barTrack}>
                <View
                  style={[
                    styles.barFill,
                    { width: `${Math.max(2, share * 100)}%` },
                    z === 'not_visible' || z === 'out_of_court' ? { backgroundColor: colors.insufficient } : null,
                  ]}
                />
              </View>
              <Text style={[type.small, styles.zonePct]}>{Math.round(share * 100)}%</Text>
            </View>
          );
        })}
      </View>
      {track.processing_s != null && (
        <Text style={[type.small, { fontSize: 11, marginTop: space.sm }]}>
          Tracking took {track.processing_s.toFixed(1)} s{track.harness_run ? ` · run ${track.harness_run}` : ''}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6, gap: space.sm },
  court: { width: '100%', aspectRatio: VIEW.w / VIEW.h, borderRadius: radius.sm, overflow: 'hidden' },
  net: { position: 'absolute', top: 2, right: 6, fontSize: 10, color: colors.muted },
  empty: {
    position: 'absolute',
    left: space.xl,
    right: space.xl,
    top: '40%',
    backgroundColor: 'rgba(255,255,255,0.9)',
    borderRadius: radius.sm,
    padding: space.md,
  },
  zoneRow: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  zoneLabel: { width: 110 },
  barTrack: { flex: 1, height: 8, borderRadius: 4, backgroundColor: colors.primarySoft, overflow: 'hidden' },
  barFill: { height: 8, borderRadius: 4, backgroundColor: colors.primary },
  zonePct: { width: 36, textAlign: 'right' },
});
