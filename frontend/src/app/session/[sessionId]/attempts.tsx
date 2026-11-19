import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AttemptRow } from '@/components/rows';
import { Button, goBack, LoadState, Screen } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { colors, radius, space, type } from '@/lib/theme';
import type { Attempt, Results } from '@/lib/types';

const FLAG_REASONS = [
  'The result looks wrong',
  'The direction is wrong',
  'Not my attempt (someone else in frame)',
  'Something else',
];

/** Figma 4.2 Review attempts, with the 4.3 flag sheet (SR-9). */
export default function Attempts() {
  const router = useRouter();
  const { sessionId, flag } = useLocalSearchParams<{ sessionId: string; flag?: string }>();
  const results = useApi(() => api.results(sessionId), [sessionId]);
  const [data, setData] = useState<Results>();
  const [flagging, setFlagging] = useState<Attempt>();

  const r = data ?? results.data;
  const label = (id: string) => r?.regions.find((x) => x.region_id === id)?.label ?? id;

  // Debug deep link: ?flag=N opens the sheet for attempt N.
  useEffect(() => {
    if (flag && results.data && !flagging) {
      setFlagging(results.data.attempts.find((a) => a.number === Number(flag)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flag, results.data]);

  const scored = r?.attempts.filter((a) => (a.outcome === 'success' || a.outcome === 'failure') && !a.flagged) ?? [];
  const excluded = r?.attempts.filter((a) => !scored.includes(a)) ?? [];

  return (
    <>
    <Screen
      title="Attempts"
      footer={
        <Button
          label="Back to Profile"
          onPress={() => (router.canGoBack() ? goBack() : router.replace(`/session/${sessionId}/results`))}
        />
      }
    >
      <LoadState loading={results.loading && !r} error={results.error} onRetry={results.reload} />
      {r && (
        <>
          <Text style={type.small}>Tap the flag on any attempt that looks misclassified.</Text>
          <Text style={type.label}>SCORED · {scored.length}</Text>
          {scored.map((a) => (
            <AttemptRow key={a.number} attempt={a} regionLabel={label(a.region_id)} onFlag={() => setFlagging(a)} />
          ))}
          <Text style={[type.label, { marginTop: space.md }]}>EXCLUDED FROM METRICS · {excluded.length}</Text>
          {excluded.map((a) => (
            <AttemptRow key={a.number} attempt={a} regionLabel={label(a.region_id)} onFlag={() => setFlagging(a)} />
          ))}
        </>
      )}
    </Screen>
      {flagging && (
        <FlagSheet
          sessionId={sessionId}
          attempt={flagging}
          onClose={() => setFlagging(undefined)}
          onFlagged={(next) => {
            setData(next);
            setFlagging(undefined);
          }}
        />
      )}
    </>
  );
}

function FlagSheet({
  sessionId,
  attempt,
  onClose,
  onFlagged,
}: {
  sessionId: string;
  attempt: Attempt;
  onClose: () => void;
  onFlagged: (r: Results) => void;
}) {
  const [reason, setReason] = useState(FLAG_REASONS[0]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const submit = async () => {
    setBusy(true);
    setError(undefined);
    try {
      onFlagged(await api.flag(sessionId, attempt.number, reason));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <View style={styles.overlay}>
      <Pressable style={{ flex: 1 }} onPress={onClose} accessibilityLabel="Close" />
      <View style={styles.sheet}>
        <View style={styles.grabber} />
        <Text style={type.h2}>Flag attempt #{String(attempt.number).padStart(2, '0')}</Text>
        <Text style={type.small}>
          Flagged attempts keep their original result for review, but they're left out of your metrics. Record the drill
          again to replace them.
        </Text>
        {FLAG_REASONS.map((r) => (
          <Pressable
            key={r}
            onPress={() => setReason(r)}
            style={[styles.reason, reason === r && styles.reasonOn]}
            accessibilityRole="radio"
            accessibilityState={{ selected: reason === r }}
          >
            <Text style={[type.body, reason === r && { color: colors.primary, fontWeight: '600' }]}>{r}</Text>
          </Pressable>
        ))}
        {error && <Text style={{ color: colors.danger }}>{error}</Text>}
        <Button label="Flag Attempt" onPress={submit} loading={busy} />
        <Button label="Cancel" variant="secondary" onPress={onClose} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: 'rgba(0,0,0,0.35)', zIndex: 10 },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: space.xl,
    gap: space.md,
  },
  grabber: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border },
  reason: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: space.lg,
  },
  reasonOn: { borderColor: colors.primary, borderWidth: 2 },
});
