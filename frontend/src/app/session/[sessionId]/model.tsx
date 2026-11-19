import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Button, Card, Label, LoadState, Notice, Screen } from '@/components/ui';
import { TrackingSetup } from '@/components/TrackingSetup';
import { SelectionControl } from '@/components/SelectionControl';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { colors, radius, space, type } from '@/lib/theme';
import type { AnalysisOptions, Clip } from '@/lib/types';
import { uploadSession } from '@/lib/upload';

function Radio({ on }: { on: boolean }) {
  return (
    <View style={[styles.radio, on && { borderColor: colors.primary }]}>
      {on && <View style={styles.radioDot} />}
    </View>
  );
}

/**
 * Prototype-only step before upload: choose which teammate's vision model
 * analyzes the clip, and which pre-recorded clip stands in for the recording.
 * This screen will not ship in production.
 */
export default function ChooseModel() {
  const router = useRouter();
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const models = useApi(api.models);
  const clips = useApi(api.clips);
  const session = useApi(() => api.session(sessionId), [sessionId]);
  const [chosenModel, setModelId] = useState<string>();
  const [chosenClip, setClipId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [analysis, setAnalysis] = useState<AnalysisOptions>();
  const modelId = chosenModel ?? (models.data?.find((m) => m.kind === 'yolo' && m.available) ?? models.data?.[0])?.id;
  const clipId = chosenClip ?? (clips.data?.find((c) => !c.synthetic) ?? clips.data?.[0])?.id;

  const model = models.data?.find((m) => m.id === modelId);
  const clip = clips.data?.find((c) => c.id === clipId);
  // Only pixel-based (harness-style) models need saved corners; court models report feet themselves.
  const blockReason = (c: Clip) =>
    model?.output_space === 'image' && !model.requires_calibration && !c.has_corners
      ? 'This model reports pixels and needs the clip\'s court corners. Add them to backend/sample_clips/corners.json.'
      : model?.requires_clip_file && c.synthetic
        ? 'This model needs a real video. Add one to backend/sample_clips.'
        : undefined;
  const clipAllowed = !!clip && !blockReason(clip);

  const upload = async () => {
    if (!modelId || !clipId) return;
    setBusy(true);
    setError(undefined);
    const r = await uploadSession(sessionId, modelId, clipId, model?.requires_calibration ? analysis : undefined);
    if (r.ok) router.replace(`/session/${sessionId}/status`);
    else if (r.retryable && !model?.requires_calibration)
      router.replace(`/session/${sessionId}/upload-error?model=${modelId}&clip=${encodeURIComponent(clipId)}`);
    else {
      setError(r.message);
      setBusy(false);
    }
  };

  const loadError = models.error ?? clips.error ?? session.error;
  return (
    <Screen
      title="Analysis model"
      back={false}
      footer={<Button label={model?.requires_calibration ? 'Analyze player positions' : 'Run simulated analysis'} onPress={upload} loading={busy} disabled={!model || !model.available || !clipAllowed || (model.requires_calibration && !analysis)} />}
    >
      <Notice title="Prototype only" tone="warning">
        Choose a tracking model for a prerecorded clip. Real models estimate player positions; attempt scoring and live recording are not part of this run.
      </Notice>
      <LoadState
        loading={models.loading || clips.loading}
        error={loadError}
        onRetry={() => (models.reload(), clips.reload(), session.reload())}
      />
      {session.data && (
        <Text style={type.small}>
          Session {session.data.id}
        </Text>
      )}

      {models.data && (
        <View>
          <Label>Vision model</Label>
          <View style={{ gap: space.sm }}>
            {models.data.map((m) => (
              <SelectionControl key={m.id} disabled={!m.available} onPress={() => { if (m.id !== modelId) { setAnalysis(undefined); setError(undefined); setModelId(m.id); } }} role="radio" label={m.name} checked={m.id === modelId}>
                <Card style={[styles.option, m.id === modelId && styles.optionOn]}>
                  <Radio on={m.id === modelId} />
                  <View style={{ flex: 1 }}>
                    <Text style={[type.body, { fontWeight: '600' }]}>
                      {m.name} <Text style={type.small}>v{m.version}</Text>
                    </Text>
                    <Text style={type.small}>{m.owner}</Text>
                    <Text style={type.small}>{m.description}</Text>
                    {!m.available && <Text style={[type.small, { color: colors.danger }]}>{m.unavailable_reason}</Text>}
                    {m.is_remote && (
                      <Text style={[type.small, { color: colors.warning, fontWeight: '600' }]}>
                        Sends frames to an outside service. Only use clips whose participants agreed (SYS-08).
                      </Text>
                    )}
                  </View>
                </Card>
              </SelectionControl>
            ))}
            {!models.data.some((m) => m.kind === 'gemini') && (
              <SelectionControl disabled checked={false} role="radio" label="Gemini — Coming soon" onPress={() => {}}>
                <Card style={[styles.option, styles.optionDisabled]}>
                  <Radio on={false} />
                  <View style={{ flex: 1 }}>
                    <Text style={[type.body, { fontWeight: '600', color: colors.muted }]}>Gemini</Text>
                    <Text style={type.small}>Liam</Text>
                    <Text style={[type.small, { fontWeight: '600' }]}>Coming soon</Text>
                    <Text style={type.small}>Not connected in this prototype.</Text>
                  </View>
                </Card>
              </SelectionControl>
            )}
          </View>
        </View>
      )}

      {clips.data && (
        <View>
          <Label>Clip to analyze</Label>
          <Text style={[type.small, { marginBottom: space.sm }]}>
            Recording is simulated, so a pre-recorded clip is sent instead.
          </Text>
          <View style={{ gap: space.sm }}>
            {clips.data.map((c) => {
              const reason = blockReason(c);
              const blocked = !!reason;
              return (
                <SelectionControl
                  key={c.id}
                  disabled={blocked}
                  onPress={() => { if (c.id !== clipId) { setAnalysis(undefined); setError(undefined); setClipId(c.id); } }}
                  role="radio"
                  label={c.name}
                  checked={c.id === clipId}
                >
                  <Card style={[styles.option, c.id === clipId && styles.optionOn, blocked && { opacity: 0.5 }]}>
                    <Radio on={c.id === clipId} />
                    <View style={{ flex: 1 }}>
                      <Text style={[type.body, { fontWeight: '600' }]}>{c.name}</Text>
                      <Text style={type.small}>
                        {reason ??
                          (c.synthetic
                            ? 'No video; works with the simulated tracker'
                            : `${c.size_mb} MB${c.has_corners ? ' · corners saved' : ''}`)}
                      </Text>
                    </View>
                  </Card>
                </SelectionControl>
              );
            })}
          </View>
        </View>
      )}
      {model?.requires_calibration && clipAllowed && clipId && <TrackingSetup key={`${model.id}:${clipId}`} model={model} clipId={clipId} onChange={setAnalysis} />}
      {error && (
        <Notice title="Can't start analysis" tone="danger">
          {error}
        </Notice>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  option: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  optionOn: { borderColor: colors.primary, borderWidth: 2 },
  optionDisabled: { backgroundColor: colors.disabled },
  radio: {
    width: 22,
    height: 22,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary },
});
