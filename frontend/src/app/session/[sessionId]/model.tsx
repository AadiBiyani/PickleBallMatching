import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button, Card, Label, LoadState, Notice, Screen } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { colors, radius, space, type } from '@/lib/theme';
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

  const model = models.data?.find((m) => m.id === modelId);
  const clip = clips.data?.find((c) => c.id === clipId);
  const clipAllowed = !!clip && !(model?.requires_clip_file && clip.synthetic);

  useEffect(() => {
    if (!modelId && models.data?.length) setModelId(models.data[0].id);
  }, [models.data, modelId]);
  useEffect(() => {
    if (!clipId && clips.data?.length) setClipId((clips.data.find((c) => !c.synthetic) ?? clips.data[0]).id);
  }, [clips.data, clipId]);

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
      footer={<Button label="Upload & Analyze" onPress={upload} loading={busy} disabled={!model || !clipAllowed} />}
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
              const blocked = !!model?.requires_clip_file && c.synthetic;
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
                        {c.synthetic
                          ? blocked
                            ? 'This model needs a real video. Add one to backend/sample_clips.'
                            : 'No video; works with the simulated tracker'
                          : `${c.size_mb} MB`}
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
