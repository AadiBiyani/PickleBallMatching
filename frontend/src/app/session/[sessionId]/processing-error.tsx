import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Cross } from '@/components/icons';
import { Button, Card, LoadState, Notice, Screen } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { colors, space, type } from '@/lib/theme';

/** Figma 3.4 Processing error: an explicit failed status with an explanation (FR-06). */
export default function ProcessingError() {
  const router = useRouter();
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const session = useApi(() => api.session(sessionId), [sessionId]);
  const s = session.data;

  return (
    <Screen
      title="Analysis"
      back={false}
      footer={
        <>
          <Button label="Record Again" onPress={() => s && router.replace(`/drill/${s.drill_id}`)} disabled={!s} />
          <Button label="Back to Dashboard" variant="secondary" onPress={() => router.replace('/')} />
        </>
      }
    >
      <View style={styles.hero}>
        <View style={styles.icon}>
          <Cross size={28} />
        </View>
        <Text style={[type.h1, { textAlign: 'center' }]}>We couldn't analyze this drill</Text>
      </View>
      <LoadState loading={session.loading} error={session.error} onRetry={session.reload} />
      {s && (
        <>
          <Notice title="What went wrong" tone="danger">
            {s.error ?? 'The analysis stopped unexpectedly.'}
          </Notice>
          <Card>
            <Text style={type.small}>Failed at: {s.steps[s.step] ?? 'unknown step'}</Text>
            <Text style={type.small}>Session {s.id}</Text>
          </Card>
          <Text style={type.small}>Your published profile, if you have one, has not changed.</Text>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { alignItems: 'center', gap: space.sm, marginVertical: space.xl },
  icon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.danger,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: space.sm,
  },
});
