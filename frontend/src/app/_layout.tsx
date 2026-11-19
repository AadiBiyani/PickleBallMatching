import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Platform, StyleSheet, useWindowDimensions, View } from 'react-native';

import { DebugPanel } from '@/components/DebugPanel';
import { FlowProvider } from '@/lib/flow';
import { colors } from '@/lib/theme';

const SHOW_DEBUG = process.env.EXPO_PUBLIC_DEBUG !== 'false';

export default function RootLayout() {
  const { width } = useWindowDimensions();
  // In a desktop browser, show the app inside a phone-sized frame.
  const framed = Platform.OS === 'web' && width > 600;
  return (
    <FlowProvider>
      <View style={[styles.outer, framed && styles.outerFramed]}>
        <View style={framed ? styles.phone : styles.app}>
          <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }} />
          {SHOW_DEBUG && !framed && <DebugPanel />}
        </View>
        {/* On desktop the debug tools sit beside the phone so they never cover the app. */}
        {SHOW_DEBUG && framed && (
          <View style={styles.dock}>
            <DebugPanel docked />
          </View>
        )}
      </View>
      <StatusBar style="dark" />
    </FlowProvider>
  );
}

const styles = StyleSheet.create({
  outer: { flex: 1, backgroundColor: colors.bg },
  outerFramed: {
    backgroundColor: '#D5D6D0',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 24,
  },
  dock: { width: 320, height: '100%', maxHeight: 844 },
  app: { flex: 1, width: '100%', overflow: 'hidden' },
  // Separate from `app` on purpose: combining flex styles collapses the width on web.
  phone: {
    width: 406, // 390 pt screen + 2 x 8 px bezel
    height: '100%',
    maxHeight: 860,
    overflow: 'hidden',
    borderRadius: 36,
    borderWidth: 8,
    borderColor: '#111',
    backgroundColor: colors.bg,
  },
});
