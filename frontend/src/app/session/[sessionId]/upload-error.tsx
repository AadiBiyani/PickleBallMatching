import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Cross } from '@/components/icons';
import { Button, Card, Notice, Screen } from '@/components/ui';
import { colors, space, type } from '@/lib/theme';
import { uploadSession } from '@/lib/upload';

/** Figma 3.2 Upload error. Retrying reuses the same session ID (FR-07). */
export default function UploadError() {
  const router = useRouter();
  const { sessionId, model = 'simulated', clip = 'synthetic' } = useLocalSearchParams<{
    sessionId: string;
    model?: string;
    clip?: string;
  }>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [tries, setTries] = useState(1);

  const retry = async () => {
    setBusy(true);
    setError(undefined);
    const r = await uploadSession(sessionId, model, clip);
    if (r.ok) {
      router.replace(`/session/${sessionId}/status`);
      return;
    }
    setTries((t) => t + 1);
    setError(r.message);
    setBusy(false);
  };

  return (
    <Screen
      title="Upload"
      back={false}
      footer={
        <>
          <Button label="Retry Upload" onPress={retry} loading={busy} />
          <Button label="Upload Later" variant="secondary" onPress={() => router.replace('/')} />
        </>
      }
    >
      <View style={styles.hero}>
        <View style={styles.icon}>
          <Cross size={28} />
        </View>
        <Text style={[type.h1, { textAlign: 'center' }]}>Upload didn't finish</Text>
        <Text style={[type.body, { color: colors.muted, textAlign: 'center' }]}>
          The connection dropped before your recording reached the server.
        </Text>
      </View>
      <Notice title="Your recording is safe" tone="primary">
        It's still saved on this device. Retrying uploads it under the same session, so nothing is recorded twice.
      </Notice>
      <Card>
        <Text style={type.small}>Session {sessionId}</Text>
        <Text style={type.small}>Failed attempts: {tries}</Text>
      </Card>
      {error && (
        <Notice title="Still not uploaded" tone="danger">
          {error}
        </Notice>
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
