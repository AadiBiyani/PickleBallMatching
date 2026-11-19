import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';

import { StepRow } from '@/components/rows';
import { Button, Card, Notice, ProgressBar, Screen } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { colors, space, type } from '@/lib/theme';
import type { Session, SessionStatus } from '@/lib/types';

const POLL_MS = 1000;

const STATUS_TEXT: Record<SessionStatus, string> = {
  awaiting_upload: 'Waiting for upload',
  uploaded: 'Uploaded',
  queued: 'Queued for analysis',
  processing: 'Processing video',
  completed: 'Analysis complete',
  failed: 'Analysis failed',
};

/** Figma 3.3 Upload & processing status (FR-06): polls the session until it finishes. */
export default function Status() {
  const router = useRouter();
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const [session, setSession] = useState<Session>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const s = await api.session(sessionId);
        if (stopped) return;
        setSession(s);
        setError(undefined);
        if (s.status === 'completed') return router.replace(`/session/${sessionId}/results`);
        if (s.status === 'failed') return router.replace(`/session/${sessionId}/processing-error`);
      } catch (e) {
        if (stopped) return;
        setError(e instanceof ApiError ? e.message : String(e));
      }
      timer = setTimeout(poll, POLL_MS);
    };
    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [sessionId, router]);

  const steps = session?.steps ?? [];
  const realTracking = !!session?.analysis;
  const stepState = (i: number) =>
    !session ? 'pending' : session.status === 'completed' || i < session.step ? 'done' : i === session.step ? 'active' : 'pending';

  return (
    <Screen
      title={realTracking ? 'Tracking player positions' : 'Simulated drill analysis'}
      back={false}
      footer={<Button label="Back to Dashboard" variant="secondary" onPress={() => router.replace('/')} />}
    >
      <Card style={{ gap: space.md }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <Text style={[type.body, { fontWeight: '600', fontSize: 17 }]}>
            {session ? STATUS_TEXT[session.status] : 'Connecting…'}
          </Text>
          <Text style={[type.stat, { color: colors.primary, fontSize: 26 }]}>
            {realTracking ? (session?.status === 'queued' ? 'Queued' : 'Working') : `${Math.round((session?.progress ?? 0) * 100)}%`}
          </Text>
        </View>
        {!realTracking && <ProgressBar value={session?.progress ?? 0} />}
        <Text style={type.small}>
          {session ? `Step ${Math.min(session.step + 1, steps.length)} of ${steps.length}. ` : ''}
          {realTracking ? 'Processing time depends on the model and selected window. No attempt scores are calculated.' : 'This is the simulated prototype flow.'}
        </Text>
      </Card>
      <Card style={{ paddingVertical: space.sm }}>
        {steps.map((label, i) => (
          <StepRow
            key={label}
            label={label}
            state={stepState(i)}
            meta={i === 0 && session?.clip_id ? (session.clip_size_mb ? `${session.clip_size_mb} MB` : 'synthetic') : undefined}
          />
        ))}
      </Card>
      {session?.model_id && <Text style={type.small}>Tracking model: {session.model_id}</Text>}
      {error ? (
        <Notice title="Can't check progress" tone="danger">
          {error} We'll keep trying.
        </Notice>
      ) : (
        <Notice title="You can leave this screen">We'll keep analyzing and your results will be waiting.</Notice>
      )}
    </Screen>
  );
}
