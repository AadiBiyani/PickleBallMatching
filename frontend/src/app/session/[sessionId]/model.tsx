import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button, Card, Label, LoadState, Notice, Screen } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
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
  const session = useApi(() => api.session(sessionId), [sessionId]);
  const [modelId, setModelId] = useState<string>();
  const [clipId, setClipId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [consent, setConsent] = useState(false);

  const model = models.data?.find((m) => m.id === modelId);
  // Remote models send frames to an outside service; the backend refuses them without this (SYS-08).
  const consentNeeded = !!model?.is_remote && !consent;
  const clip = clips.data?.find((c) => c.id === clipId);
  // Only pixel-based (harness-style) models need saved corners; court models report feet themselves.
  const blockReason = (c: Clip) =>
    model?.output_space === 'image' && !c.has_corners
      ? 'This model reports pixels and needs the clip\'s court corners. Add them to backend/sample_clips/corners.json.'
      : model?.requires_clip_file && c.synthetic
        ? 'This model needs a real video. Add one to backend/sample_clips.'
        : undefined;
  const clipAllowed = !!clip && !blockReason(clip);

  useEffect(() => {
    if (!modelId && models.data?.length) setModelId(models.data[0].id);
  }, [models.data, modelId]);
  useEffect(() => setConsent(false), [modelId]);
  useEffect(() => {
    if (!clipId && clips.data?.length)
      setClipId((clips.data.find((c) => !c.synthetic) ?? clips.data[0]).id);
  }, [clips.data, clipId]);

  const upload = async () => {
    if (!modelId || !clipId) return;
    setBusy(true);
    setError(undefined);
    const consentConfirmed = !!model?.is_remote && consent;
    const r = await uploadSession(sessionId, modelId, clipId, consentConfirmed);
    if (r.ok) router.replace(`/session/${sessionId}/status`);
    else if (r.retryable)
      router.replace(
        `/session/${sessionId}/upload-error?model=${encodeURIComponent(modelId)}&clip=${encodeURIComponent(clipId)}` +
          (consentConfirmed ? '&consent=1' : ''),
      );
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
      footer={
        <Button
          label="Upload & Analyze"
          onPress={upload}
          loading={busy}
          disabled={!model || !clipAllowed || consentNeeded}
        />
      }
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
              <Pressable key={m.id} onPress={() => setModelId(m.id)} accessibilityRole="radio" accessibilityState={{ selected: m.id === modelId }}>
                <Card style={[styles.option, m.id === modelId && styles.optionOn]}>
                  <Radio on={m.id === modelId} />
                  <View style={{ flex: 1 }}>
                    <Text style={[type.body, { fontWeight: '600' }]}>
                      {m.name} <Text style={type.small}>v{m.version}</Text>
                    </Text>
                    <Text style={type.small}>{m.owner}</Text>
                    <Text style={type.small}>{m.description}</Text>
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
      {model?.is_remote && (
        <Pressable
          onPress={() => setConsent((c) => !c)}
          accessibilityRole="checkbox"
          accessibilityState={{ checked: consent }}
        >
          <Card style={[styles.option, consent && styles.optionOn]}>
            <View style={[styles.checkbox, consent && styles.checkboxOn]}>
              {consent && <Text style={styles.checkmark}>✓</Text>}
            </View>
            <Text style={[type.small, { flex: 1 }]}>
              Everyone visible in this clip agreed to it being sent to {model.name}'s outside service (SYS-08).
            </Text>
          </Card>
        </Pressable>
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
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 4,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxOn: { borderColor: colors.primary, backgroundColor: colors.primary },
  checkmark: { color: colors.card, fontSize: 14, fontWeight: '700', lineHeight: 16 },
});
