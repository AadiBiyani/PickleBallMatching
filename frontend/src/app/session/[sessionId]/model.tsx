import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button, Card, Label, LoadState, Notice, Screen } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi, useDemoClip } from '@/lib/hooks';
import { colors, radius, space, type } from '@/lib/theme';
import type { Clip } from '@/lib/types';
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
  // When the fixed demo clip exists, it is the "recording": no clip picker.
  const demo = useDemoClip();
  const session = useApi(() => api.session(sessionId), [sessionId]);
  const [modelId, setModelId] = useState<string>();
  const [clipId, setClipId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const model = models.data?.find((m) => m.id === modelId);
  const clip = clips.data?.find((c) => c.id === clipId);
  // Mirrors VisionModel.clip_problem() in the backend, which re-checks on upload.
  const blockReason = (c: Clip): string | undefined => {
    if (!model) return undefined;
    if (model.requires_clip_file && c.synthetic) return 'This model needs a real video. Add one to backend/sample_clips.';
    if (model.needs_corners && !c.has_corners)
      return "No court corners saved for this clip. Add them to backend/sample_clips/corners.json.";
    if (model.needs_export && !c.exports.includes(model.id))
      return 'No precomputed run for this clip. Add it to backend/sample_clips/exports.json.';
    return undefined;
  };
  const clipAllowed = !!clip && !blockReason(clip);

  useEffect(() => {
    if (!modelId && models.data?.length) setModelId((models.data.find((m) => m.available) ?? models.data[0]).id);
  }, [models.data, modelId]);
  // Keep the selected clip usable by the selected model: prefer a real clip it accepts.
  useEffect(() => {
    if (demo.clip) {
      if (clipId !== demo.clip.id) setClipId(demo.clip.id);
      return;
    }
    if (!clips.data?.length || !model) return;
    if (clip && !blockReason(clip)) return;
    const usable = clips.data.filter((c) => !blockReason(c));
    const next = usable.find((c) => !c.synthetic) ?? usable[0];
    if (next && next.id !== clipId) setClipId(next.id);
    else if (!clipId) setClipId(clips.data[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clips.data, model?.id, demo.clip?.id]);

  const upload = async () => {
    if (!modelId || !clipId) return;
    setBusy(true);
    setError(undefined);
    const r = await uploadSession(sessionId, modelId, clipId);
    if (r.ok) router.replace(`/session/${sessionId}/status`);
    else if (r.retryable)
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
      footer={<Button label="Upload & Analyze" onPress={upload} loading={busy} disabled={!model || !model.available || !clipAllowed} />}
    >
      <Notice title="Prototype only" tone="warning">
        Pick which team member's tracking model analyzes this recording. Production will use one chosen model.
      </Notice>
      <LoadState
        loading={models.loading || clips.loading}
        error={loadError}
        onRetry={() => (models.reload(), clips.reload(), session.reload())}
      />
      {session.data && (
        <Text style={type.small}>
          Recording saved · session {session.data.id} · {session.data.feed_method.replace('_', ' ')}
        </Text>
      )}

      {models.data && (
        <View>
          <Label>Vision model</Label>
          <View style={{ gap: space.sm }}>
            {models.data.map((m) => (
              <Pressable
                key={m.id}
                disabled={!m.available}
                onPress={() => setModelId(m.id)}
                accessibilityRole="radio"
                accessibilityState={{ selected: m.id === modelId, disabled: !m.available }}
              >
                <Card style={[styles.option, m.id === modelId && styles.optionOn, !m.available && { opacity: 0.55 }]}>
                  <Radio on={m.id === modelId} />
                  <View style={{ flex: 1 }}>
                    <Text style={[type.body, { fontWeight: '600' }]}>
                      {m.name} <Text style={type.small}>{m.version === 'harness' ? 'via court harness' : `v${m.version}`}</Text>
                    </Text>
                    <Text style={type.small}>{m.owner}</Text>
                    <Text style={type.small}>{m.description}</Text>
                    {!m.available && (
                      <Text style={[type.small, { color: colors.danger, fontWeight: '600' }]}>
                        Unavailable: {m.unavailable_reason}
                      </Text>
                    )}
                    {m.is_remote && (
                      <Text style={[type.small, { color: colors.warning, fontWeight: '600' }]}>
                        Sends frames to an outside service. Only use clips whose participants agreed (SYS-08).
                      </Text>
                    )}
                  </View>
                </Card>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      {demo.clip && (
        <View>
          <Label>Recording</Label>
          <Card style={styles.option}>
            <View style={{ flex: 1 }}>
              <Text style={[type.body, { fontWeight: '600' }]}>{demo.clip.name}</Text>
              <Text style={type.small}>
                The clip shown on the camera screens. Recording is simulated, so this pre-recorded clip is analyzed.
              </Text>
              {blockReason(demo.clip) && (
                <Text style={[type.small, { color: colors.danger, fontWeight: '600' }]}>{blockReason(demo.clip)}</Text>
              )}
            </View>
          </Card>
        </View>
      )}

      {!demo.clip && !demo.loading && clips.data && (
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
                <Pressable
                  key={c.id}
                  disabled={blocked}
                  onPress={() => setClipId(c.id)}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: c.id === clipId, disabled: blocked }}
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
                </Pressable>
              );
            })}
          </View>
        </View>
      )}
      {error && (
        <Notice title="Can't start the upload" tone="danger">
          {error}
        </Notice>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  option: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  optionOn: { borderColor: colors.primary, borderWidth: 2 },
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
