import { useEventListener } from 'expo';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useEffect } from 'react';
import { StyleSheet } from 'react-native';

/**
 * Plays the demo clip as the simulated camera feed. Always muted, so browsers
 * allow it to start without a click, and without controls, so it reads as a
 * camera rather than a video player.
 */
export function ClipVideo({
  uri,
  playing,
  loop = false,
  onEnd,
}: {
  uri: string;
  playing: boolean;
  loop?: boolean;
  onEnd?: () => void;
}) {
  const player = useVideoPlayer(uri, (p) => {
    p.muted = true;
    p.loop = loop;
    if (playing) p.play();
  });

  useEffect(() => {
    player.loop = loop;
    if (playing) player.play();
    else player.pause();
  }, [player, playing, loop]);

  useEventListener(player, 'playToEnd', () => onEnd?.());

  return <VideoView player={player} nativeControls={false} contentFit="contain" style={styles.fill} />;
}

const styles = StyleSheet.create({
  // On web the view is a <video>, a replaced element: `inset: 0` alone leaves it at its
  // natural size (e.g. 1280x800, clipped). An explicit 100% size makes it fill the feed.
  fill: { position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' },
});
