import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, radius, space } from '@/lib/theme';
import { ClipVideo } from './ClipVideo';
import { CameraCourt, type PlayerFrame } from './court';
import { ChevronLeft, StatusDot } from './icons';
import { goBack } from './ui';

export function Pill({ children, dot }: { children: ReactNode; dot?: string }) {
  return (
    <View style={styles.pill}>
      {dot && <StatusDot color={dot} size={9} />}
      <Text style={styles.pillText}>{children}</Text>
    </View>
  );
}

/** Plays the demo clip as the camera feed (see ClipVideo). */
export interface FeedVideo {
  uri: string;
  playing: boolean;
  loop?: boolean;
  onEnd?: () => void;
}

/**
 * Dark camera layout shared by Figma 2.2-2.5. Real capture is out of scope for
 * the prototype: the "feed" plays the pre-recorded demo clip when a playable
 * copy exists, and otherwise shows a static court illustration.
 */
export function CameraScreen({
  left,
  right,
  frame,
  showBall,
  overlay,
  panel,
  full = false,
  back = true,
  video,
}: {
  left?: ReactNode;
  right?: ReactNode;
  frame: PlayerFrame;
  showBall?: boolean;
  overlay?: ReactNode;
  panel?: ReactNode;
  full?: boolean;
  back?: boolean;
  video?: FeedVideo;
}) {
  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <View style={[styles.feed, full ? { flex: 1 } : { height: 420 }]}>
        {video ? (
          <ClipVideo uri={video.uri} playing={video.playing} loop={video.loop} onEnd={video.onEnd} />
        ) : (
          <CameraCourt frame={frame} showBall={showBall} />
        )}
        <View style={styles.topBar}>
          <View style={styles.topLeft}>
            {back && (
              <Pressable onPress={goBack} hitSlop={10} accessibilityRole="button" accessibilityLabel="Back">
                <ChevronLeft color="#fff" />
              </Pressable>
            )}
            {left}
          </View>
          {right}
        </View>
        {overlay && <View style={styles.overlay}>{overlay}</View>}
        <Text style={styles.simulated}>{video ? 'Pre-recorded clip (simulated camera)' : 'Simulated camera view'}</Text>
      </View>
      {panel && <View style={styles.panel}>{panel}</View>}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.camera },
  feed: { width: '100%', overflow: 'hidden' },
  topBar: {
    position: 'absolute',
    top: space.md,
    left: space.lg,
    right: space.lg,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  topLeft: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(10,14,20,0.8)',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: radius.pill,
  },
  pillText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  overlay: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, alignItems: 'center', justifyContent: 'center' },
  simulated: { position: 'absolute', bottom: 8, right: 12, color: 'rgba(255,255,255,0.55)', fontSize: 11 },
  panel: {
    flex: 1,
    backgroundColor: colors.card,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    marginTop: -20,
    padding: space.xl,
    gap: space.md,
  },
});
