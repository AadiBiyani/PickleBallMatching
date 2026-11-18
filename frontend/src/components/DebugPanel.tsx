import { useRouter, type Href } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { api, ApiError } from '@/lib/api';
import { useFlow } from '@/lib/flow';
import { colors, radius, space, type } from '@/lib/theme';
import type { Scenario } from '@/lib/types';

const DEFAULT_DRILL = 'lateral-prescribed';

interface Jump {
  id: string;
  label: string;
  /** Returns the route to open; may create a backend session in the needed state first. */
  go: () => Promise<string>;
}

const s = (state: Parameters<typeof api.debugSession>[0], scenario?: Scenario) => api.debugSession(state, scenario);

const GROUPS: { title: string; jumps: Jump[] }[] = [
  {
    title: '1 · Start',
    jumps: [
      { id: '1.0', label: 'Dashboard', go: async () => '/' },
      { id: '1.0b', label: 'Dashboard - profile published', go: async () => (await s('published'), '/') },
      { id: '1.2', label: 'Drill list', go: async () => '/drills' },
      { id: '1.3', label: 'Drill instructions', go: async () => `/drill/${DEFAULT_DRILL}` },
      { id: '1.4', label: 'Readiness checklist', go: async () => `/drill/${DEFAULT_DRILL}/checklist` },
    ],
  },
  {
    title: '2 · Record (simulated)',
    jumps: [
      { id: '2.2', label: 'Camera check - not ready', go: async () => `/record/camera?drillId=${DEFAULT_DRILL}` },
      { id: '2.3', label: 'Camera check - ready', go: async () => `/record/camera?drillId=${DEFAULT_DRILL}&ready=1` },
      { id: '2.4', label: 'Countdown', go: async () => `/record/countdown?drillId=${DEFAULT_DRILL}` },
      { id: '2.5', label: 'Recording', go: async () => `/record/recording?drillId=${DEFAULT_DRILL}` },
    ],
  },
  {
    title: '3 · Upload & analysis',
    jumps: [
      { id: '3.1', label: 'Choose vision model (prototype)', go: async () => `/session/${(await s('awaiting_upload')).id}/model` },
      { id: '3.2', label: 'Upload error', go: async () => `/session/${(await s('awaiting_upload', 'upload_error')).id}/upload-error` },
      { id: '3.3', label: 'Upload & processing status', go: async () => `/session/${(await s('processing')).id}/status` },
      { id: '3.4', label: 'Processing error', go: async () => `/session/${(await s('failed')).id}/processing-error` },
    ],
  },
  {
    title: '4 · Results',
    jumps: [
      { id: '4.1', label: 'Provisional coverage profile', go: async () => `/session/${(await s('completed')).id}/results` },
      { id: '4.1b', label: 'Not enough valid data', go: async () => `/session/${(await s('completed', 'insufficient_data')).id}/results` },
      { id: '4.2', label: 'Review attempts', go: async () => `/session/${(await s('completed')).id}/attempts` },
      { id: '4.3', label: 'Flag an attempt', go: async () => `/session/${(await s('completed')).id}/attempts?flag=1` },
      { id: '4.4', label: 'Assessment published', go: async () => `/session/${(await s('published')).id}/published` },
    ],
  },
  {
    title: '5 · Partners (placeholder)',
    jumps: [{ id: '5.2', label: 'Partner matches (dummy)', go: async () => '/partners' }],
  },
];

const SCENARIOS: { id: Scenario; label: string }[] = [
  { id: 'normal', label: 'Normal' },
  { id: 'upload_error', label: 'Upload fails once' },
  { id: 'processing_error', label: 'Processing fails' },
  { id: 'insufficient_data', label: 'Not enough data' },
];

/**
 * Prototype-only tools: jump to any screen and pick the scenario the next
 * recording follows. `docked` renders it beside the phone frame (desktop
 * browser); otherwise it is a small corner button that opens a sheet.
 */
export function DebugPanel({ docked = false }: { docked?: boolean }) {
  const router = useRouter();
  const { scenario, setScenario } = useFlow();
  const [open, setOpen] = useState(docked);
  const [busy, setBusy] = useState<string>();
  const [error, setError] = useState<string>();

  const jump = async (j: Jump) => {
    setBusy(j.id);
    setError(undefined);
    try {
      const href = await j.go();
      if (!docked) setOpen(false);
      router.push(href as Href);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(undefined);
    }
  };

  const reset = async () => {
    setError(undefined);
    try {
      await api.debugReset();
      if (!docked) setOpen(false);
      router.replace('/');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  };

  if (!open) {
    return (
      <Pressable
        style={docked ? styles.dockButton : styles.fab}
        onPress={() => setOpen(true)}
        accessibilityRole="button"
        accessibilityLabel="Open debug panel"
      >
        <Text style={styles.fabText}>DEBUG</Text>
      </Pressable>
    );
  }

  return (
    <View style={docked ? styles.dock : styles.overlay}>
      <View style={docked ? styles.dockSheet : styles.sheet}>
        <View style={styles.sheetHeader}>
          <Text style={type.h2}>Debug</Text>
          <Pressable onPress={() => setOpen(false)} hitSlop={10} accessibilityRole="button">
            <Text style={{ color: colors.primary, fontWeight: '600' }}>{docked ? 'Hide' : 'Close'}</Text>
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={{ gap: space.lg, paddingBottom: space.xl }}>
          <View>
            <Text style={type.label}>NEXT RECORDING FOLLOWS</Text>
            <View style={styles.chips}>
              {SCENARIOS.map((sc) => (
                <Pressable
                  key={sc.id}
                  onPress={() => setScenario(sc.id)}
                  style={[styles.chip, scenario === sc.id && styles.chipOn]}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: scenario === sc.id }}
                >
                  <Text style={[styles.chipText, scenario === sc.id && { color: '#fff' }]}>{sc.label}</Text>
                </Pressable>
              ))}
            </View>
          </View>
          {error && <Text style={{ color: colors.danger }}>{error}</Text>}
          {GROUPS.map((g) => (
            <View key={g.title}>
              <Text style={type.label}>{g.title.toUpperCase()}</Text>
              {g.jumps.map((j) => (
                <Pressable key={j.id} style={styles.jump} onPress={() => jump(j)} disabled={!!busy}>
                  <Text style={styles.jumpId}>{j.id}</Text>
                  <Text style={[type.body, { flex: 1 }]}>{j.label}</Text>
                  {busy === j.id && <Text style={type.small}>…</Text>}
                </Pressable>
              ))}
            </View>
          ))}
          <Pressable onPress={reset} style={[styles.jump, { justifyContent: 'center' }]}>
            <Text style={{ color: colors.danger, fontWeight: '600' }}>Reset demo data</Text>
          </Pressable>
        </ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: 'absolute',
    right: 6,
    top: 6,
    backgroundColor: '#111827',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: radius.pill,
    opacity: 0.7,
  },
  dockButton: {
    alignSelf: 'flex-start',
    backgroundColor: '#111827',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: radius.pill,
  },
  dock: { flex: 1 },
  dockSheet: {
    flex: 1,
    backgroundColor: colors.bg,
    borderRadius: radius.lg,
    padding: space.xl,
    borderWidth: 1,
    borderColor: colors.border,
  },
  fabText: { color: colors.accent, fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  overlay: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: 'rgba(0,0,0,0.35)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: space.xl,
    maxHeight: '85%',
  },
  sheetHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: space.md },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm, marginTop: space.sm },
  chip: { borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 12, paddingVertical: 6, backgroundColor: colors.card },
  chipOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontSize: 13, fontWeight: '600', color: colors.text },
  jump: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
    backgroundColor: colors.card,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.md,
    marginTop: 6,
  },
  jumpId: { width: 36, fontWeight: '700', color: colors.primary },
});
