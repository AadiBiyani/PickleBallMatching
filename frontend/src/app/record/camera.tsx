import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { CameraScreen, Pill } from '@/components/CameraScreen';
import { CheckTile } from '@/components/rows';
import { Button, Notice } from '@/components/ui';
import { useDemoClip } from '@/lib/hooks';
import { colors, space, type } from '@/lib/theme';

type CheckId = 'court' | 'player' | 'stable' | 'quality';

const CHECKS: { id: CheckId; label: string; fix: [string, string] }[] = [
  { id: 'court', label: 'Court visible', fix: ['Court lines not in view', 'Tilt the phone down until both sidelines and the net are visible.'] },
  { id: 'player', label: 'Player visible', fix: ['Player not fully visible', 'Move about 1 m toward the center mark so your feet and paddle stay in frame.'] },
  { id: 'stable', label: 'Camera stable', fix: ['Camera is moving', "Mount the phone on a tripod and don't touch it while recording."] },
  { id: 'quality', label: 'Image quality', fix: ['Image too dark or blurry', 'Face the camera away from the sun and wipe the lens.'] },
];

/**
 * Figma 2.2 / 2.3 Camera check (FR-04). Checks are simulated: tap a tile to
 * mimic a scene change. Recording stays disabled until every check passes.
 */
export default function CameraCheck() {
  const router = useRouter();
  const { drillId, ready } = useLocalSearchParams<{ drillId: string; ready?: string }>();
  const [checks, setChecks] = useState<Record<CheckId, boolean>>({
    court: true,
    player: ready === '1',
    stable: true,
    quality: true,
  });
  const failing = CHECKS.find((c) => !checks[c.id]);
  const allPass = !failing;
  const { previewUri } = useDemoClip();

  return (
    <CameraScreen
      video={previewUri ? { uri: previewUri, playing: true, loop: true } : undefined}
      frame={checks.player ? 'ok' : 'bad'}
      left={<Pill dot={allPass ? '#3BD47E' : colors.danger}>{allPass ? 'Ready' : 'Not ready'}</Pill>}
      right={<Pill>Live preview</Pill>}
      panel={
        <>
          <Text style={type.h2}>Camera setup check</Text>
          <View style={{ gap: space.sm }}>
            {[CHECKS.slice(0, 2), CHECKS.slice(2)].map((pair) => (
              <View key={pair[0].id} style={{ flexDirection: 'row', gap: space.sm }}>
                {pair.map((c) => (
                  <CheckTile
                    key={c.id}
                    label={c.label}
                    ok={checks[c.id]}
                    onPress={() => setChecks((s) => ({ ...s, [c.id]: !s[c.id] }))}
                  />
                ))}
              </View>
            ))}
          </View>
          {failing ? (
            <Notice title={failing.fix[0]} tone="danger">
              {failing.fix[1]}
            </Notice>
          ) : (
            <Notice title="Ready to record" tone="success">
              Keep the phone still. Recording stops automatically after 60 seconds.
            </Notice>
          )}
          <Button
            label="Start Recording"
            disabled={!allPass}
            onPress={() => router.replace(`/record/countdown?drillId=${drillId}`)}
          />
          <Text style={[type.small, { fontSize: 11, textAlign: 'center' }]}>
            Prototype: tap a check to simulate a scene change.
          </Text>
        </>
      }
    />
  );
}
