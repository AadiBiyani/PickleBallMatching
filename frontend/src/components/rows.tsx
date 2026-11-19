import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, space, type } from '@/lib/theme';
import type { Attempt } from '@/lib/types';
import { Check, Cross, Flag } from './icons';

/** Camera setup check tile (Figma UI/CheckRow). */
export function CheckTile({ label, ok, onPress }: { label: string; ok: boolean; onPress?: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole={onPress ? 'switch' : undefined}
      accessibilityState={{ checked: ok }}
      style={[styles.tile, { backgroundColor: ok ? colors.successSoft : colors.dangerSoft }]}
    >
      <View style={[styles.badge, { backgroundColor: ok ? colors.success : colors.danger }]}>
        {ok ? <Check size={12} /> : <Cross size={11} />}
      </View>
      <Text style={[type.body, { flex: 1 }]}>{label}</Text>
    </Pressable>
  );
}

/** Checkbox row (Figma UI/ChecklistItem). */
export function ChecklistItem({ label, checked, onToggle }: { label: string; checked: boolean; onToggle: () => void }) {
  return (
    <Pressable
      onPress={onToggle}
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      style={styles.checkItem}
    >
      <View style={[styles.checkbox, checked && { backgroundColor: colors.primary, borderColor: colors.primary }]}>
        {checked && <Check size={14} />}
      </View>
      <Text style={[type.body, { flex: 1, fontWeight: '500' }]}>{label}</Text>
    </Pressable>
  );
}

/** Processing pipeline step (done / active / pending). */
export function StepRow({ label, state, meta }: { label: string; state: 'done' | 'active' | 'pending'; meta?: string }) {
  return (
    <View style={styles.step}>
      {state === 'done' ? (
        <View style={[styles.badge, styles.stepBadge, { backgroundColor: colors.success }]}>
          <Check size={13} />
        </View>
      ) : state === 'active' ? (
        <ActivityIndicator size="small" color={colors.primary} style={styles.stepBadge} />
      ) : (
        <View style={[styles.stepBadge, styles.pending]} />
      )}
      <Text
        style={[
          type.body,
          { flex: 1 },
          state === 'active' && { fontWeight: '700' },
          state === 'pending' && { color: colors.muted },
        ]}
      >
        {label}
      </Text>
      {meta ? <Text style={type.small}>{meta}</Text> : null}
    </View>
  );
}

const OUTCOME_TEXT: Record<Attempt['outcome'], string> = {
  success: 'Returned',
  failure: 'Missed',
  invalid_feed: 'Invalid feed',
  uncertain: 'Outcome uncertain',
};

/** One attempt in the review list (Figma UI/AttemptRow). */
export function AttemptRow({
  attempt,
  regionLabel,
  onFlag,
}: {
  attempt: Attempt;
  regionLabel: string;
  onFlag?: () => void;
}) {
  const excluded = attempt.outcome === 'invalid_feed' || attempt.outcome === 'uncertain' || attempt.flagged;
  const scoredOutcome = attempt.outcome === 'success' || attempt.outcome === 'failure';
  const title = scoredOutcome ? `${regionLabel} feed · ${OUTCOME_TEXT[attempt.outcome]}` : OUTCOME_TEXT[attempt.outcome];
  let detail: string;
  if (attempt.flagged) detail = `Flagged: ${attempt.flag_reason}. Original result: ${OUTCOME_TEXT[attempt.outcome]}.`;
  else if (attempt.reason) detail = attempt.reason;
  else detail = `Reached in ${attempt.travel_time_s} s · ${attempt.lateral_ft} ft lateral`;
  const num = `#${String(attempt.number).padStart(2, '0')}`;
  return (
    <View style={styles.attempt}>
      <View style={[styles.attemptNum, { backgroundColor: excluded ? colors.warningSoft : colors.successSoft }]}>
        <Text style={{ fontWeight: '700', color: excluded ? colors.warning : colors.success }}>{num}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={[type.body, { fontWeight: '600' }]}>{title}</Text>
        <Text style={type.small}>{detail}</Text>
      </View>
      {onFlag && (
        <Pressable
          onPress={onFlag}
          disabled={attempt.flagged}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel={attempt.flagged ? `Attempt ${attempt.number} flagged` : `Flag attempt ${attempt.number}`}
        >
          <Flag filled={attempt.flagged} color={attempt.flagged ? colors.warning : colors.muted} />
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    borderRadius: radius.sm,
    paddingHorizontal: space.md,
    paddingVertical: space.md,
  },
  badge: { width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  checkItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.lg,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  step: { flexDirection: 'row', alignItems: 'center', gap: space.md, paddingVertical: 7 },
  stepBadge: { width: 22, height: 22 },
  pending: { borderRadius: 11, borderWidth: 1.5, borderColor: colors.border, borderStyle: 'dashed' },
  attempt: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.md,
  },
  attemptNum: { width: 46, height: 46, borderRadius: radius.sm, alignItems: 'center', justifyContent: 'center' },
});
