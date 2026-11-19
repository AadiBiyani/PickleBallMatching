import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ChevronRight, CourtGlyph } from '@/components/icons';
import { Card, LoadState, Screen } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { colors, radius, space, type } from '@/lib/theme';

/** Figma 1.2 Choose a drill. Drill definitions come from the API (FR-03). */
export default function DrillList() {
  const router = useRouter();
  const drills = useApi(api.drills);

  return (
    <Screen title="Choose a drill" back={false}>
      <Text style={type.small}>
        Each drill uses a fixed number of feeds and the same setup, so results are comparable across players.
      </Text>
      <LoadState loading={drills.loading} error={drills.error} onRetry={drills.reload} />
      {drills.data?.map((d) => (
        <Pressable key={d.id} onPress={() => router.push(`/drill/${d.id}`)} accessibilityRole="button">
          <Card style={styles.row}>
            <View style={styles.icon}>
              <CourtGlyph />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[type.body, { fontWeight: '600' }]}>{d.name}</Text>
              <Text style={type.small}>{d.summary}</Text>
            </View>
            <ChevronRight />
          </Card>
        </Pressable>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  icon: {
    width: 48,
    height: 48,
    borderRadius: radius.sm,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
