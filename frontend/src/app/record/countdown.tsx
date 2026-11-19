import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { CameraScreen, Pill } from '@/components/CameraScreen';

/** Figma 2.4 Countdown before recording starts. */
export default function Countdown() {
  const router = useRouter();
  const { drillId } = useLocalSearchParams<{ drillId: string }>();
  const [n, setN] = useState(3);

  useEffect(() => {
    if (n === 0) {
      router.replace(`/record/recording?drillId=${drillId}`);
      return;
    }
    const t = setTimeout(() => setN((x) => x - 1), 1000);
    return () => clearTimeout(t);
  }, [n, drillId, router]);

  return (
    <CameraScreen
      full
      frame="ok"
      left={<Pill>Get set</Pill>}
      overlay={
        <View style={styles.center}>
          <Text style={styles.count}>{Math.max(n, 1)}</Text>
          <Text style={styles.hint}>Go to the center mark</Text>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', backgroundColor: 'rgba(10,14,20,0.55)', paddingHorizontal: 40, paddingVertical: 24, borderRadius: 24 },
  count: { color: '#fff', fontSize: 96, fontWeight: '800' },
  hint: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
