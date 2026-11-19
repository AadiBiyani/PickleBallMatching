import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ChecklistItem } from '@/components/rows';
import { Button, Label, Screen } from '@/components/ui';
import { useFlow } from '@/lib/flow';
import { colors, radius, space, type } from '@/lib/theme';
import type { FeedMethod } from '@/lib/types';

const ITEMS = [
  'I have a paddle and 20 balls, or a loaded ball machine',
  'A feeder or ball machine is ready',
  'My phone is on a tripod or stable stand',
  "I'm wearing clothing that contrasts with the court",
];

const FEED_METHODS: { id: FeedMethod; label: string }[] = [
  { id: 'human_feeder', label: 'Human feeder' },
  { id: 'ball_machine', label: 'Ball machine' },
];

/** Figma 1.4 Readiness checklist, plus the feed method stored with the session (FR-05). */
export default function Checklist() {
  const router = useRouter();
  const { drillId } = useLocalSearchParams<{ drillId: string }>();
  const { feedMethod, setFeedMethod } = useFlow();
  const [checked, setChecked] = useState(ITEMS.map(() => false));
  const allChecked = checked.every(Boolean);

  return (
    <Screen
      title="Before you start"
      footer={
        <Button
          label="Start Camera Setup"
          disabled={!allChecked}
          onPress={() => router.push(`/record/camera?drillId=${drillId}`)}
        />
      }
    >
      <Text style={type.small}>Confirm you're set up. You'll position the camera on the next screen.</Text>
      {ITEMS.map((label, i) => (
        <ChecklistItem
          key={label}
          label={label}
          checked={checked[i]}
          onToggle={() => setChecked((c) => c.map((v, j) => (j === i ? !v : v)))}
        />
      ))}
      <View style={{ marginTop: space.md }}>
        <Label>Who is feeding?</Label>
        <View style={styles.segment}>
          {FEED_METHODS.map((m) => {
            const on = feedMethod === m.id;
            return (
              <Pressable
                key={m.id}
                onPress={() => setFeedMethod(m.id)}
                style={[styles.segmentItem, on && styles.segmentOn]}
                accessibilityRole="radio"
                accessibilityState={{ selected: on }}
              >
                <Text style={[type.body, { fontWeight: '600', color: on ? '#fff' : colors.text }]}>{m.label}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  segment: {
    flexDirection: 'row',
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 4,
  },
  segmentItem: { flex: 1, alignItems: 'center', paddingVertical: 10, borderRadius: radius.sm },
  segmentOn: { backgroundColor: colors.primary },
});
