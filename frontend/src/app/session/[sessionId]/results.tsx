import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { CoverageCourt, TrackCourt } from '@/components/court';
import { Button, Card, Chip, Label, LoadState, Notice, Row, Screen, StatTile } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApi, useReloadOnFocus } from '@/lib/hooks';
import { pct, space, type } from '@/lib/theme';
import type { Results } from '@/lib/types';

function exclusionText(r: Results) {
  const { invalid_feed, uncertain, flagged } = r.exclusions;
  const parts = [
    invalid_feed && `${invalid_feed} invalid feed${invalid_feed > 1 ? 's' : ''}`,
    uncertain && `${uncertain} uncertain`,
    flagged && `${flagged} flagged by you`,
  ].filter(Boolean);
  const excluded = invalid_feed + uncertain + flagged;
  return `${r.scored} of ${r.total_attempts} attempts scored.` + (excluded ? ` ${excluded} excluded (${parts.join(', ')}).` : '');
}

/** Figma 4.1 Provisional coverage profile, and 4.1b when there is not enough valid data. */
export default function ResultsScreen() {
  const router = useRouter();
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const results = useApi(() => api.results(sessionId), [sessionId]);
  const track = useApi(() => api.track(sessionId), [sessionId]);
  useReloadOnFocus(results.reload);
  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string>();
  const r = results.data;

  const publish = async () => {
    setPublishing(true);
    setPublishError(undefined);
    try {
      await api.publish(sessionId);
      router.replace(`/session/${sessionId}/published`);
    } catch (e) {
      setPublishError(e instanceof ApiError ? e.message : String(e));
      setPublishing(false);
    }
  };

  const insufficientRegions = r?.regions.filter((x) => !x.sufficient) ?? [];
  const footer = r && (
    <>
      {r.published ? (
        <Button label="View Partner Matches" onPress={() => router.push('/partners')} />
      ) : r.sufficient ? (
        <Button label="Publish to Profile" onPress={publish} loading={publishing} />
      ) : (
        <Button label="Record Again" onPress={() => router.replace(`/drill/${r.drill_id}`)} />
      )}
      <Button label="Review Attempts" variant="secondary" onPress={() => router.push(`/session/${sessionId}/attempts`)} />
    </>
  );

  return (
    <Screen title="Coverage profile" onBack={() => router.replace('/')} footer={footer}>
      <LoadState loading={results.loading && !r} error={results.error} onRetry={results.reload} />
      {r && (
        <>
          <Row gap={8}>
            {r.published ? (
              <Chip label="PUBLISHED" tone="success" />
            ) : r.sufficient ? (
              <Chip label="PROVISIONAL" tone="warning" />
            ) : (
              <Chip label="NOT ENOUGH DATA" tone="danger" />
            )}
            <Text style={[type.small, { flexShrink: 1 }]}>{r.drill_name}</Text>
          </Row>

          {!r.sufficient && (
            <Notice title="Not enough valid data to publish" tone="warning">
              {insufficientRegions.map((x) => x.label).join(', ')}{' '}
              {insufficientRegions.length === 1 ? 'has' : 'have'} fewer than {r.min_scored_per_region} scored attempts.
              Record the drill again to complete your profile. Your published profile was not changed.
            </Notice>
          )}

          <Card>
            <CoverageCourt regions={r.regions} minScored={r.min_scored_per_region} />
          </Card>

          <Row>
            <StatTile
              label="Return success"
              value={pct(r.success_rate)}
              caption={`${r.successes} of ${r.scored} scored · 95% range ${pct(r.ci_low)}-${pct(r.ci_high)}`}
            />
            <StatTile
              label="Response time"
              value={r.avg_response_time_s != null ? `${r.avg_response_time_s.toFixed(2)} s` : '-'}
              caption="Avg feed to first move (proxy)"
            />
          </Row>

          <Notice title="Scored vs. excluded">{exclusionText(r)}</Notice>
          {publishError && (
            <Notice title="Couldn't publish" tone="danger">
              {publishError}
            </Notice>
          )}

          <Card>
            {track.data ? (
              <TrackCourt points={track.data} />
            ) : (
              <LoadState loading={track.loading} error={track.error} onRetry={track.reload} />
            )}
            <Text style={[type.small, { marginTop: space.sm, fontSize: 12 }]}>
              {r.track.model_id === 'simulated'
                ? 'Synthetic positions from the simulated tracker.'
                : `From ${r.track.kind}:${r.track.model_id} at ${r.track.sample_fps} frame/s, mapped to court feet with ` +
                  "the clip's saved corners. Not yet checked against labeled positions."}
            </Text>
          </Card>

          <Card>
            <Label>Limitations</Label>
            {r.limitations.map((l) => (
              <Text key={l} style={[type.small, { marginBottom: 4 }]}>
                • {l}
              </Text>
            ))}
            <View style={{ marginTop: space.sm }}>
              <Text style={[type.small, { fontSize: 11 }]}>
                Model {r.track.model_id} v{r.track.model_version} · {r.track.frames} frames, {r.track.missing_frames}{' '}
                without a player position · analysis {r.analysis_version} · drill v{r.drill_version}
              </Text>
            </View>
          </Card>
        </>
      )}
    </Screen>
  );
}
