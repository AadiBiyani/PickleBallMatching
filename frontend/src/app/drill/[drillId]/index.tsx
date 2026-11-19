import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Line, Rect } from 'react-native-svg';

import { Button, Card, Chip, Label, LoadState, Screen } from '@/components/ui';
import { useDrill } from '@/lib/hooks';
import { colors, space, type } from '@/lib/theme';

function StartDiagram() {
  return (
    <Svg width={92} height={84} viewBox="0 0 92 84">
      <Rect x={2} y={2} width={88} height={80} fill={colors.primarySoft} stroke={colors.primary} strokeWidth={2} />
      <Line x1={2} y1={42} x2={90} y2={42} stroke={colors.text} strokeWidth={2} />
      <Line x1={2} y1={28} x2={90} y2={28} stroke={colors.primary} strokeWidth={1} />
      <Line x1={2} y1={56} x2={90} y2={56} stroke={colors.primary} strokeWidth={1} />
      <Line x1={46} y1={2} x2={46} y2={28} stroke={colors.primary} strokeWidth={1} />
      <Line x1={46} y1={56} x2={46} y2={82} stroke={colors.primary} strokeWidth={1} />
      <Circle cx={46} cy={78} r={6} fill={colors.accent} stroke={colors.text} strokeWidth={1} />
    </Svg>
  );
}

/** Figma 1.3 Drill instructions (FR-03: shows the drill's current version). */
export default function DrillInstructions() {
  const router = useRouter();
  const { drillId } = useLocalSearchParams<{ drillId: string }>();
  const { drill: d, loading, error, reload } = useDrill(drillId);

  return (
    <Screen
      title={d?.name ?? 'Drill'}
      footer={d && <Button label="Continue" onPress={() => router.push(`/drill/${d.id}/checklist`)} />}
    >
      <LoadState loading={loading} error={error ?? (!loading && !d ? 'Drill not found.' : undefined)} onRetry={reload} />
      {d && (
        <>
          <View style={{ flexDirection: 'row', gap: space.sm }}>
            <Chip label={d.stage === 'prescribed' ? 'Prescribed feeds' : 'Reactive feeds'} />
            <Chip label={`Drill v${d.version}`} />
          </View>
          <Card>
            <Label>Purpose</Label>
            <Text style={type.body}>{d.purpose}</Text>
          </Card>
          <Card>
            <Label>Equipment</Label>
            <View style={styles.chips}>
              {d.equipment.map((e) => (
                <Chip key={e} label={e} />
              ))}
            </View>
          </Card>
          <Card>
            <Label>Starting position</Label>
            <View style={{ flexDirection: 'row', gap: space.md, alignItems: 'center' }}>
              <StartDiagram />
              <Text style={[type.body, { flex: 1 }]}>{d.starting_position}</Text>
            </View>
          </Card>
          <Card>
            <Label>Steps</Label>
            {d.steps.map((s, i) => (
              <Text key={s} style={[type.body, { marginBottom: 6 }]}>
                {i + 1}. {s}
              </Text>
            ))}
            <Text style={[type.small, { marginTop: space.sm }]}>
              Target: {d.target_area}. {d.feed_count} feeds; recording stops automatically after {d.max_recording_s} s.
            </Text>
          </Card>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
});
