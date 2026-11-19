import { useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Linking, Text, View } from 'react-native';
import Svg, { Circle, Line, Polyline, Rect, Text as SvgText } from 'react-native-svg';

import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { colors, space, type } from '@/lib/theme';
import { trailSegments } from '@/lib/tracking-view';
import type { Results } from '@/lib/types';
import { Button, Card, LoadState, Notice, Row, Screen, StatTile } from './ui';
import { SelectionControl } from './SelectionControl';

const PLAYER_COLORS = ['#D6EF3C', '#FFB58A', '#87E4FF', '#E1BBFF', '#FFFFFF', '#FF8EB4', '#9AFFCD', '#FFC857'];

export function TrackingResults({ results }: { results: Results }) {
  const router = useRouter();
  const track = useApi(() => api.track(results.session_id), [results.session_id]);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [player, setPlayer] = useState('all');
  const [downloadError, setDownloadError] = useState<string>();
  const rows = track.data ?? [];
  const frames = useMemo(() => [...new Set((track.data ?? []).map((r) => r.source_frame_index!))].sort((a, b) => a - b), [track.data]);
  const current = frames[cursor];
  const visiblePlayers = results.track.players.filter((p) => player === 'all' || p === player);
  const currentRows = rows.filter((r) => r.source_frame_index === current && visiblePlayers.includes(r.player_id));
  useEffect(() => {
    if (!playing) return;
    const timer = setTimeout(() => {
      if (cursor < frames.length - 1) setCursor((v) => v + 1);
      if (cursor >= frames.length - 2) setPlaying(false);
    }, 1000 / results.track.sample_fps);
    return () => clearTimeout(timer);
  }, [playing, cursor, frames.length, results.track.sample_fps]);
  const download = async (name: string) => {
    try { setDownloadError(undefined); await Linking.openURL(api.artifactUrl(results.session_id, name)); }
    catch (e) { setDownloadError(String(e)); }
  };

  return <Screen title="Player tracking results" onBack={() => router.replace('/')}
    footer={<Button label="Analyze another clip" variant="secondary" onPress={() => router.replace('/')} />}>
    <Notice title="Real position estimates">{results.track.model_id} · {results.track.players.length} {results.track.kind === 'mediapipe' ? 'detected pose' : 'selected players'}. Return success, ball tracking and coverage scores are unavailable.</Notice>
    {results.track.kind === 'mediapipe' && <Notice title="Identity is not locked" tone="warning">This model can switch people between samples. The dot represents the detected pose, not a consistently selected player.</Notice>}
    <Row>
      <StatTile label="Sampled frames" value={String(results.track.frames)} caption={`${results.track.sample_fps} samples/second`} />
      <StatTile label="Missing positions" value={String(results.track.missing_frames)} caption={`of ${results.track.observations} player observations`} />
    </Row>
    <LoadState loading={track.loading} error={track.error} onRetry={track.reload} />
    {!!rows.length && <>
      <Card style={{ gap: space.sm }}>
        <Text style={type.h2}>Court positions</Text>
        <Text style={type.small}>Far baseline at top. Coordinates are in feet. Trails stop at missing observations.</Text>
        <Svg width="100%" height={360} viewBox="-3 -3 26 50" accessibilityLabel="Court diagram showing player position estimates">
          <Rect x={0} y={0} width={20} height={44} fill={colors.courtFill} stroke={colors.text} strokeWidth={0.15} />
          <Rect x={0} y={15} width={20} height={14} fill="#204566" />
          {[15, 29].map((y) => <Line key={y} x1={0} x2={20} y1={y} y2={y} stroke="white" strokeWidth={0.12} />)}
          <Line x1={10} x2={10} y1={0} y2={15} stroke="white" strokeWidth={0.12} />
          <Line x1={10} x2={10} y1={29} y2={44} stroke="white" strokeWidth={0.12} />
          <Line x1={-1} x2={21} y1={22} y2={22} stroke={colors.accent} strokeWidth={0.3} />
          <SvgText x={21} y={22} fill={colors.text} fontSize={1.2}>Net</SvgText>
          {visiblePlayers.flatMap((p) => trailSegments(rows, p, current).map((segment, i) => <Polyline key={`${p}-${i}`} points={segment.map((xy) => xy.join(',')).join(' ')} stroke={PLAYER_COLORS[results.track.players.indexOf(p) % 8]} strokeWidth={0.2} opacity={0.55} fill="none" />))}
          {currentRows.filter((r) => r.x_ft !== null && r.y_ft !== null).map((r) => <Circle key={r.player_id} cx={r.x_ft!} cy={r.y_ft!} r={0.6} fill={PLAYER_COLORS[results.track.players.indexOf(r.player_id) % 8]} stroke={colors.text} strokeWidth={0.12} />)}
        </Svg>
        <Text accessibilityLiveRegion="polite" style={type.body}>Sample {cursor + 1} of {frames.length} · source frame {current} · {(currentRows[0]?.time_s ?? 0).toFixed(2)} s</Text>
        <View style={{ flexDirection: 'row', gap: space.sm }}>
          <View style={{ flex: 1 }}><Button label="Previous" disabled={cursor === 0} variant="secondary" onPress={() => { setPlaying(false); setCursor((v) => v - 1); }} /></View>
          <View style={{ flex: 1 }}><Button label={playing ? 'Pause' : 'Play'} onPress={() => { if (cursor === frames.length - 1) setCursor(0); setPlaying(!playing); }} /></View>
          <View style={{ flex: 1 }}><Button label="Next" disabled={cursor === frames.length - 1} variant="secondary" onPress={() => { setPlaying(false); setCursor((v) => v + 1); }} /></View>
        </View>
        <Text style={type.body}>Show players</Text>
        {['all', ...results.track.players].map((p) => <SelectionControl key={p} role="radio" label={p === 'all' ? 'All players' : p.replaceAll('_', ' ')} checked={player === p} onPress={() => setPlayer(p)}><View style={{ paddingVertical: space.sm }}>
          <Text style={[type.body, { color: player === p ? colors.primary : colors.text }]}>{player === p ? '●' : '○'} {p === 'all' ? 'All players' : p.replaceAll('_', ' ')}</Text>
        </View></SelectionControl>)}
        {currentRows.map((r) => <View key={r.player_id} style={{ borderTopWidth: 1, borderColor: colors.border, paddingTop: space.sm }}>
          <Text style={[type.body, { fontWeight: '600' }]}>{r.player_id.replaceAll('_', ' ')}</Text>
          <Text style={type.small}>{r.x_ft === null ? 'Position unavailable' : `x ${r.x_ft.toFixed(2)} ft, y ${r.y_ft!.toFixed(2)} ft`} · {r.zone.replaceAll('_', ' ')}</Text>
          <Text style={type.small}>{r.reason ?? `Reference: ${r.point_source.replaceAll('_', ' ')}`}</Text>
        </View>)}
        <Text style={type.small}>The summary above always includes every player. Points beyond the diagram remain in the exports.</Text>
      </Card>
      <Card style={{ gap: space.sm }}>
        <Text style={type.h2}>Download results</Text>
        {['track.csv', 'track.json', 'provenance.json', ...(results.track.kind === 'yolo' ? ['positions.json', 'positions.csv'] : [])].map((name) => <Button key={name} label={`Download ${name}`} variant="secondary" onPress={() => download(name)} />)}
        {downloadError && <Notice title="Download failed" tone="danger">{downloadError}</Notice>}
      </Card>
    </>}
    <Card style={{ gap: space.sm }}>
      <Text style={type.h2}>Measurement limitations</Text>
      {results.limitations.map((l) => <Text key={l} style={type.small}>• {l}</Text>)}
    </Card>
  </Screen>;
}
