import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Button, Card, Chip, LoadState, Notice, Screen } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi, useReloadOnFocus } from '@/lib/hooks';
import { colors, radius, space, type } from '@/lib/theme';

// Placeholder data. Partner matching (SYS-06) is not part of this prototype's flow.
const SAMPLE = [
  { name: 'Sample player A', score: 0.82, skill: '3.5-4.0', side: 'Prefers right', why: 'Strong wide-right coverage where yours is weakest' },
  { name: 'Sample player B', score: 0.76, skill: '3.5', side: 'Either side', why: 'Similar skill; covers center well' },
  { name: 'Sample player C', score: 0.71, skill: '4.0', side: 'Prefers left', why: 'Overlaps your left-side strength' },
];

/** Dummy stand-in for Figma 5.2 "Your matches". */
export default function Partners() {
  const router = useRouter();
  const profile = useApi(api.profile);
  useReloadOnFocus(profile.reload);

  return (
    <Screen title="Your matches" back={false}>
      <Notice title="Sample data" tone="warning">
        Partner matching isn't part of this prototype. These cards show the planned layout only.
      </Notice>
      <LoadState loading={profile.loading && !profile.data} error={profile.error} />
      {!profile.loading && !profile.data && !profile.error ? (
        <>
          <Notice title="Publish a coverage profile first">
            Recommendations unlock after you publish a drill assessment.
          </Notice>
          <Button label="Record New Drill" onPress={() => router.push('/drills')} />
        </>
      ) : (
        profile.data &&
        SAMPLE.map((m, i) => (
          <Card key={m.name} style={{ gap: space.sm }}>
            <View style={styles.top}>
              <View style={styles.rank}>
                <Text style={{ color: colors.primary, fontWeight: '700' }}>{i + 1}</Text>
              </View>
              <Text style={[type.body, { fontWeight: '600', flex: 1 }]}>{m.name}</Text>
              <Text style={[type.h2, { color: colors.primary }]}>{Math.round(m.score * 100)}</Text>
            </View>
            <Text style={type.small}>{m.why}</Text>
            <View style={{ flexDirection: 'row', gap: space.sm }}>
              <Chip label={`Skill ${m.skill}`} />
              <Chip label={m.side} />
            </View>
          </Card>
        ))
      )}
      <Text style={[type.small, { fontSize: 12 }]}>
        A compatibility score is not a predicted chance of winning.
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  top: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  rank: {
    width: 30,
    height: 30,
    borderRadius: radius.pill,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
