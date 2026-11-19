import { useEffect, useMemo, useRef, useState } from 'react';
import { Image, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import Svg, { Circle, Polygon, Rect, Text as SvgText } from 'react-native-svg';

import { api, API_URL } from '@/lib/api';
import { colors, radius, space, type } from '@/lib/theme';
import { imagePoint } from '@/lib/tracking-view';
import type { AnalysisOptions, ClipPreview, VisionModelInfo } from '@/lib/types';
import { Button, Card, Notice } from './ui';
import { SelectionControl } from './SelectionControl';

const CORNERS = ['Far-left', 'Far-right', 'Near-right', 'Near-left'];
const emptyCorners = (): string[][] => CORNERS.map(() => ['', '']);

export function TrackingSetup({ clipId, model, onChange }: {
  clipId: string; model: VisionModelInfo; onChange: (options: AnalysisOptions | undefined) => void;
}) {
  const [frame, setFrame] = useState('0');
  const [limit, setLimit] = useState('300');
  const [fps, setFps] = useState('1');
  const [preview, setPreview] = useState<ClipPreview>();
  const [corners, setCorners] = useState<string[][]>(emptyCorners);
  const [activeCorner, setActiveCorner] = useState(0);
  const [selected, setSelected] = useState<number[]>([]);
  const [width, setWidth] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const generation = useRef(0);
  useEffect(() => () => { generation.current += 1; }, []);

  const points = useMemo(() => corners.map((pair) => pair.every((v) => v.trim() !== '' && Number.isFinite(Number(v)))
    ? pair.map(Number) as [number, number] : null), [corners]);
  const ready = !!preview && !!frame.trim() && Number(frame) === preview.frame_index && points.every((p) => p !== null)
    && Number.isInteger(Number(limit)) && Number(limit) >= 1 && Number(limit) <= 1800
    && Number(fps) > 0 && Number(fps) <= 10
    && (model.selection_mode !== 'multiple' || selected.length > 0);

  useEffect(() => {
    onChange(ready && preview ? {
      start_frame: preview.frame_index, max_frames: Number(limit), sample_fps: Number(fps),
      calibration: { width: preview.source.width, height: preview.source.height, corners_px: points as [number, number][] },
      selections: preview.candidates.filter((c) => selected.includes(c.candidate_id)).map((c) => c.bbox),
    } : undefined);
  }, [ready, preview, points, selected, limit, fps, onChange]);

  const load = async () => {
    if (!Number.isInteger(Number(frame)) || Number(frame) < 0 || !frame.trim()) {
      setError('Enter a nonnegative whole frame number.'); return;
    }
    const ticket = ++generation.current;
    setBusy(true); setError(undefined); setPreview(undefined); setSelected([]); setCorners(emptyCorners());
    try {
      const result = await api.preview(clipId, model.id, Number(frame));
      if (ticket !== generation.current) return;
      setPreview(result);
      if (result.corners_px) setCorners(result.corners_px.map((p) => p.map(String)));
      setActiveCorner(0);
    } catch (e) { if (ticket === generation.current) setError(String(e)); }
    finally { if (ticket === generation.current) setBusy(false); }
  };
  const edit = (index: number, axis: number, value: string) => setCorners((old) => old.map((p, i) => i === index ? p.map((v, a) => a === axis ? value : v) : p));
  const toggle = (id: number) => setSelected((old) => old.includes(id) ? old.filter((v) => v !== id) : old.length < 8 ? [...old, id] : old);

  return <View style={{ gap: space.md }}>
    <Card style={{ gap: space.sm }}>
      <Text style={type.h2}>Set up tracking</Text>
      <Text style={type.small}>Choose a starting frame where the court and players are visible. All positions use the original video coordinates.</Text>
      <Text style={type.body}>Starting frame</Text>
      <TextInput accessibilityLabel="Starting frame" value={frame} onChangeText={setFrame} keyboardType="numeric" style={styles.input} />
      <Button label="Load frame preview" loading={busy} onPress={load} />
      {error && <Notice title="Preview unavailable" tone="danger">{error}</Notice>}
    </Card>
    {preview && <>
      <Card style={{ gap: space.sm }}>
        <Text style={type.h2}>Mark the four court corners</Text>
        <Text style={type.small}>Tap {CORNERS[activeCorner].toLowerCase()} on the image, or enter its x/y coordinates below. Order: far-left, far-right, near-right, near-left.</Text>
        {preview.corners_px && <Notice title="Saved calibration">Saved corners are shown below. Verify them against this clip. These marks do not establish measured accuracy.</Notice>}
        <Pressable accessibilityLabel={`Court preview; edit ${CORNERS[activeCorner]} coordinates below for keyboard access`}
          onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
          onPress={(e) => {
            const [x, y] = imagePoint(e.nativeEvent.locationX, e.nativeEvent.locationY, width, preview.source.width, preview.source.height);
            setCorners((old) => old.map((p, i) => i === activeCorner ? [x.toFixed(1), y.toFixed(1)] : p));
            setActiveCorner((activeCorner + 1) % 4);
          }} style={{ width: '100%', aspectRatio: preview.source.width / preview.source.height, backgroundColor: colors.camera }}>
          <Image pointerEvents="none" source={{ uri: API_URL + preview.image_url }} style={StyleSheet.absoluteFill} resizeMode="contain" />
          <Svg pointerEvents="none" style={StyleSheet.absoluteFill} viewBox={`0 0 ${preview.source.width} ${preview.source.height}`}>
            {points.every(Boolean) && <Polygon points={points.map((p) => p!.join(',')).join(' ')} fill={colors.accent} fillOpacity={0.12} stroke={colors.accent} strokeWidth={6} />}
            {points.map((p, i) => p && <Circle key={i} cx={p[0]} cy={p[1]} r={14} fill={colors.accent} stroke={colors.text} strokeWidth={3} />)}
            {preview.candidates.map((c) => <Rect key={c.candidate_id} x={c.bbox.x1} y={c.bbox.y1} width={c.bbox.x2 - c.bbox.x1} height={c.bbox.y2 - c.bbox.y1}
              stroke={selected.includes(c.candidate_id) ? colors.accent : '#FFFFFF'} strokeWidth={5} fill="none" />)}
            {preview.candidates.map((c) => <SvgText key={`label-${c.candidate_id}`} x={c.bbox.x1} y={Math.max(30, c.bbox.y1 - 10)} fill={colors.accent} stroke={colors.text} strokeWidth={1} fontSize={Math.max(34, preview.source.width / width * 14)} fontWeight="bold">{c.candidate_id + 1}</SvgText>)}
          </Svg>
        </Pressable>
        <Text style={type.small}>{preview.source.width} × {preview.source.height} · {preview.source.frame_count} frames · {preview.source.fps.toFixed(1)} FPS</Text>
        {CORNERS.map((name, i) => <View key={name} style={{ gap: 4 }}>
          <Pressable onPress={() => setActiveCorner(i)} accessibilityRole="button" accessibilityLabel={`Mark ${name} on image`}>
            <Text style={[type.body, { color: activeCorner === i ? colors.primary : colors.text }]}>{i + 1}. {name}{activeCorner === i ? ' (next click)' : ''}</Text>
          </Pressable>
          <View style={styles.pair}>{[0, 1].map((axis) => <TextInput key={axis} accessibilityLabel={`${name} ${axis === 0 ? 'x' : 'y'}`} placeholder={axis === 0 ? 'x pixels' : 'y pixels'} value={corners[i][axis]} onChangeText={(v) => edit(i, axis, v)} keyboardType="numeric" style={[styles.input, { flex: 1 }]} />)}</View>
        </View>)}
        <Button label="Reset corners" variant="secondary" onPress={() => { setCorners(emptyCorners()); setActiveCorner(0); }} />
      </Card>
      {model.selection_mode === 'multiple' ? <Card style={{ gap: space.sm }}>
        <Text style={type.h2}>Select on-court players</Text>
        <Text style={type.small}>Numbers match the boxes above. Select up to eight people; leave spectators unchecked. Selection order follows the numbered boxes.</Text>
        {!preview.candidates.length && <Notice title="No players detected" tone="warning">Try a different starting frame with visible players.</Notice>}
        {preview.candidates.map((c) => <SelectionControl key={c.candidate_id} onPress={() => toggle(c.candidate_id)} role="checkbox" label={`Player candidate ${c.candidate_id + 1}`} checked={selected.includes(c.candidate_id)}><View style={[styles.choice, selected.includes(c.candidate_id) && { borderColor: colors.primary, backgroundColor: colors.primarySoft }]}>
          <Text style={type.body}>{selected.includes(c.candidate_id) ? '✓' : '○'} Player candidate {c.candidate_id + 1}</Text>
        </View></SelectionControl>)}
      </Card> : <Notice title="One detected pose, no identity lock" tone="warning">MediaPipe chooses a pose separately at each sample. It can switch people in a doubles clip. Use single-player footage for an interpretable demonstration.</Notice>}
      <Card style={{ gap: space.sm }}>
        <Text style={type.body}>Maximum frames to process (1–1800)</Text>
        <TextInput accessibilityLabel="Maximum frames" value={limit} onChangeText={setLimit} keyboardType="numeric" style={styles.input} />
        <Text style={type.body}>Court samples per second (up to 10)</Text>
        <TextInput accessibilityLabel="Court samples per second" value={fps} onChangeText={setFps} keyboardType="numeric" style={styles.input} />
        <Text style={type.small}>YOLO tracks every frame before sampling. Processing stops at the end of the clip if it is shorter than the requested window.</Text>
      </Card>
    </>}
  </View>;
}

const styles = StyleSheet.create({
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, padding: space.md, color: colors.text, backgroundColor: colors.card, minWidth: 0 },
  pair: { flexDirection: 'row', gap: space.sm },
  choice: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, padding: space.md },
});
