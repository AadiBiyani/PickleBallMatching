import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { CameraScreen, Pill } from '@/components/CameraScreen';
import { Button } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useFlow } from '@/lib/flow';
import { useDrill } from '@/lib/hooks';
import { colors, space } from '@/lib/theme';

const FEED_INTERVAL_S = 3;

const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

/**
 * Figma 2.5 Recording (simulated). Stops automatically at the drill's recording
 * cap. Stopping creates the session with its metadata (FR-05).
 */
export default function Recording() {
  const router = useRouter();
  const { drillId } = useLocalSearchParams<{ drillId: string }>();
  const { drill } = useDrill(drillId);
  const { feedMethod, scenario } = useFlow();
  const startedAt = useRef(new Date().toISOString());
  const [elapsed, setElapsed] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  const cap = drill?.max_recording_s ?? 60;
  const feeds = drill?.feed_count ?? 20;
  const feed = Math.min(feeds, Math.floor(elapsed / FEED_INTERVAL_S) + 1);

  const stop = async () => {
    if (!drill || saving) return;
    setSaving(true);
    setError(undefined);
    try {
      const s = await api.createSession({
        drill_id: drill.id,
        drill_version: drill.version,
        feed_method: feedMethod,
        capture_started_at: startedAt.current,
        capture_ended_at: new Date().toISOString(),
        scenario,
      });
      router.replace(`/session/${s.id}/model`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
      setSaving(false);
    }
  };

  useEffect(() => {
    if (saving) return;
    if (elapsed >= cap) {
      stop();
      return;
    }
    const t = setTimeout(() => setElapsed((x) => x + 1), 1000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elapsed, cap, saving]);

  return (
    <CameraScreen
      full
      back={false}
      frame="ok"
      showBall
      left={<Pill dot={colors.danger}>REC {mmss(elapsed)} / {mmss(cap)}</Pill>}
      right={<Pill>Feed {feed} of {feeds}</Pill>}
      overlay={
        <View style={styles.bottom}>
          <Text style={styles.hint}>
            {error ?? `Tracking you and the ball. Recording stops on its own at ${cap} s.`}
          </Text>
          <Button label={error ? 'Try Saving Again' : 'Stop Recording'} variant="danger" loading={saving} onPress={stop} />
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  bottom: { position: 'absolute', left: space.xl, right: space.xl, bottom: space.xl, gap: space.md },
  hint: { color: '#fff', fontSize: 14, textAlign: 'center', textShadowColor: '#000', textShadowRadius: 4 },
});
