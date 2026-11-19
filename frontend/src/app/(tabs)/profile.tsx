import { useRouter } from 'expo-router';
import { Text } from 'react-native';

import { CoverageCourt } from '@/components/court';
import { Button, Card, Chip, LoadState, Notice, Row, Screen, StatTile } from '@/components/ui';
import { api } from '@/lib/api';
import { useApi, useReloadOnFocus } from '@/lib/hooks';
import { pct, type } from '@/lib/theme';

const MIN_SCORED = 5;

/** Published coverage profile (the version used for matching, FR-15). */
export default function Profile() {
  const router = useRouter();
  const profile = useApi(api.profile);
  useReloadOnFocus(profile.reload);
  const p = profile.data;

  return (
    <Screen title="Your profile" back={false}>
      <LoadState loading={profile.loading && !p} error={profile.error} onRetry={profile.reload} />
      {!profile.loading && !profile.error && !p && (
        <>
          <Notice title="No published profile yet">
            Record a drill and publish the results to build the profile that partner matching uses.
          </Notice>
          <Button label="Record New Drill" onPress={() => router.push('/drills')} />
        </>
      )}
      {p && (
        <>
          <Row gap={8}>
            <Chip label={`Version ${p.version}`} tone="success" />
            <Text style={type.small}>
              {p.drill_name} · {new Date(p.published_at).toLocaleDateString()}
            </Text>
          </Row>
          <Card>
            <CoverageCourt regions={p.regions} minScored={MIN_SCORED} />
          </Card>
          <Row>
            <StatTile label="Return success" value={pct(p.success_rate)} caption={`${p.scored} scored attempts`} />
            <StatTile label="Analysis" value={p.analysis_version} caption="Stored with this version" />
          </Row>
        </>
      )}
    </Screen>
  );
}
