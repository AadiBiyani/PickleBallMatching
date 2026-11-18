import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Check } from '@/components/icons';
import { Button, LoadState, Row, Screen, StatTile } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { colors, pct, space, type } from '@/lib/theme';

/** Figma 4.4 Assessment published (FR-15: a new profile version). */
export default function Published() {
  const router = useRouter();
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const profile = useApi(api.profile);
  const p = profile.data;
  const isThisSession = p?.session_id === sessionId;

  return (
    <Screen
      footer={
        <>
          <Button label="View Partner Matches" onPress={() => router.replace('/partners')} />
          <Button label="Back to Dashboard" variant="secondary" onPress={() => router.replace('/')} />
        </>
      }
    >
      <View style={styles.hero}>
        <View style={styles.halo}>
          <View style={styles.badge}>
            <Check size={34} />
          </View>
        </View>
        <Text style={[type.h1, { textAlign: 'center' }]}>Assessment published</Text>
        <Text style={[type.body, { color: colors.muted, textAlign: 'center' }]}>
          Your court coverage profile is on your player profile and will be used to recommend partners with
          complementary coverage.
        </Text>
      </View>
      <LoadState loading={profile.loading} error={profile.error} onRetry={profile.reload} />
      {p && (
        <>
          <Row>
            <StatTile label="Return success" value={pct(p.success_rate)} caption={`${p.scored} scored attempts`} />
            <StatTile label="Profile version" value={`v${p.version}`} caption={p.drill_name} />
          </Row>
          {!isThisSession && (
            <Text style={type.small}>Note: your latest published version comes from a different session.</Text>
          )}
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { alignItems: 'center', gap: space.md, marginTop: 60, marginBottom: space.lg },
  halo: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.successSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.success,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
