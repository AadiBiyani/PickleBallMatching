import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ChevronRight } from '@/components/icons';
import { Button, Card, Chip, Screen } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi, useReloadOnFocus } from '@/lib/hooks';
import { colors, pct, radius, space, type } from '@/lib/theme';

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
}

/** Figma 1.0 Dashboard, and 1.0b once a profile is published. */
export default function Dashboard() {
  const router = useRouter();
  const profile = useApi(api.profile);
  useReloadOnFocus(profile.reload);
  const p = profile.data;

  return (
    <Screen>
      <View style={{ marginTop: space.lg, marginBottom: space.sm }}>
        <Text style={type.h1}>{greeting()}, Jordan</Text>
        <Text style={[type.body, { color: colors.muted }]}>
          {p ? 'Your coverage profile is live.' : 'Ready to measure your court coverage?'}
        </Text>
      </View>

      <View style={styles.hero}>
        <Text style={styles.heroLabel}>{p ? 'IMPROVE YOUR PROFILE' : 'NEW ASSESSMENT'}</Text>
        <Text style={styles.heroTitle}>Record a standardized drill</Text>
        <Text style={styles.heroBody}>
          About 5 minutes including setup; the recording itself is up to 60 seconds. We'll analyze your movement and
          build your court coverage profile.
        </Text>
        <Button label="Record New Drill" variant="accent" onPress={() => router.push('/drills')} />
      </View>

      {profile.error ? (
        <Card>
          <Text style={[type.small, { color: colors.danger }]}>{profile.error}</Text>
        </Card>
      ) : (
        <Pressable disabled={!p} onPress={() => router.push('/profile')}>
          <Card style={styles.row}>
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={[type.body, { fontWeight: '600' }]}>Coverage profile</Text>
              {p ? (
                <>
                  <Chip label={`Published · v${p.version}`} tone="success" />
                  <Text style={type.small}>
                    {p.drill_name} · {pct(p.success_rate)} return success from {p.scored} scored attempts
                  </Text>
                </>
              ) : (
                <Text style={type.small}>
                  No published profile yet. Complete one drill with enough valid attempts to publish.
                </Text>
              )}
            </View>
            {p && <ChevronRight />}
          </Card>
        </Pressable>
      )}

      <Pressable disabled={!p} onPress={() => router.push('/partners')}>
        <Card style={styles.row}>
          <View style={{ flex: 1, gap: 4 }}>
            <Text style={[type.body, { fontWeight: '600' }]}>Partner recommendations</Text>
            <Text style={type.small}>
              {p ? 'See players whose coverage complements yours.' : 'Unlocks after you publish a coverage profile.'}
            </Text>
          </View>
          {p && <ChevronRight />}
        </Card>
      </Pressable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { backgroundColor: colors.primary, borderRadius: radius.lg, padding: space.xl, gap: space.sm },
  heroLabel: { color: colors.accent, fontSize: 12, fontWeight: '700', letterSpacing: 1 },
  heroTitle: { color: '#fff', fontSize: 22, fontWeight: '700' },
  heroBody: { color: '#E6ECFF', fontSize: 15, lineHeight: 21, marginBottom: space.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: space.md },
});
