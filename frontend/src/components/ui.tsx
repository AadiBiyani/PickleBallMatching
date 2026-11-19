import { router } from 'expo-router';
import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, radius, space, type } from '@/lib/theme';
import { ChevronLeft, StatusDot } from './icons';

/** Go back if there is history (e.g. a debug jump may have none), else go home. */
export function goBack() {
  if (router.canGoBack()) router.back();
  else router.replace('/');
}

interface ScreenProps {
  title?: string;
  back?: boolean;
  onBack?: () => void;
  footer?: ReactNode;
  children: ReactNode;
  scroll?: boolean;
}

/** Standard screen: centered title with back arrow, scrolling body, pinned footer. */
export function Screen({ title, back = true, onBack, footer, children, scroll = true }: ScreenProps) {
  const Body = scroll ? ScrollView : View;
  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      {title !== undefined && (
        <View style={styles.header}>
          {back ? (
            <Pressable accessibilityRole="button" accessibilityLabel="Back" onPress={onBack ?? goBack} style={styles.back} hitSlop={12}>
              <ChevronLeft />
            </Pressable>
          ) : (
            <View style={styles.back} />
          )}
          <Text style={type.title} numberOfLines={1}>
            {title}
          </Text>
          <View style={styles.back} />
        </View>
      )}
      <Body style={styles.body} contentContainerStyle={scroll ? styles.bodyContent : undefined}>
        {scroll ? children : <View style={[styles.bodyContent, { flex: 1 }]}>{children}</View>}
      </Body>
      {footer && <View style={styles.footer}>{footer}</View>}
    </SafeAreaView>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Label({ children }: { children: ReactNode }) {
  return <Text style={[type.label, { marginBottom: space.sm }]}>{String(children).toUpperCase()}</Text>;
}

type ButtonVariant = 'primary' | 'secondary' | 'accent' | 'danger';

export function Button({
  label,
  onPress,
  variant = 'primary',
  disabled = false,
  loading = false,
}: {
  label: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  loading?: boolean;
}) {
  const v = disabled ? buttonVariants.disabled : buttonVariants[variant];
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [styles.button, v.container, pressed && { opacity: 0.85 }]}
    >
      {loading ? <ActivityIndicator color={v.text.color} /> : <Text style={[styles.buttonText, v.text]}>{label}</Text>}
    </Pressable>
  );
}

const buttonVariants = {
  primary: { container: { backgroundColor: colors.primary }, text: { color: '#fff' } },
  secondary: {
    container: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border },
    text: { color: colors.text },
  },
  accent: { container: { backgroundColor: colors.accent }, text: { color: colors.text } },
  danger: { container: { backgroundColor: colors.danger }, text: { color: '#fff' } },
  disabled: { container: { backgroundColor: colors.disabled }, text: { color: colors.disabledText } },
};

export function Chip({ label, tone = 'primary' }: { label: string; tone?: 'primary' | 'warning' | 'success' | 'danger' }) {
  const t = tones[tone];
  return (
    <View style={[styles.chip, { backgroundColor: t.bg }]}>
      <Text style={[styles.chipText, { color: t.fg }]}>{label}</Text>
    </View>
  );
}

const tones = {
  primary: { bg: colors.primarySoft, fg: colors.primary },
  warning: { bg: colors.warningSoft, fg: colors.warning },
  success: { bg: colors.successSoft, fg: colors.success },
  danger: { bg: colors.dangerSoft, fg: colors.danger },
};

/** Callout with a colored dot, e.g. "You can leave this screen". */
export function Notice({
  title,
  children,
  tone = 'primary',
}: {
  title: string;
  children?: ReactNode;
  tone?: 'primary' | 'warning' | 'success' | 'danger';
}) {
  const t = tones[tone];
  return (
    <View style={[styles.notice, { backgroundColor: t.bg }]}>
      <View style={{ paddingTop: 5 }}>
        <StatusDot color={t.fg} size={9} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={[type.body, { fontWeight: '600', color: t.fg }]}>{title}</Text>
        {children ? <Text style={[type.small, { color: colors.text }]}>{children}</Text> : null}
      </View>
    </View>
  );
}

export function StatTile({ label, value, caption }: { label: string; value: string; caption?: string }) {
  return (
    <Card style={{ flex: 1, padding: space.lg }}>
      <Text style={type.small}>{label}</Text>
      <Text style={type.stat}>{value}</Text>
      {caption ? <Text style={[type.small, { fontSize: 12 }]}>{caption}</Text> : null}
    </Card>
  );
}

export function ProgressBar({ value }: { value: number }) {
  return (
    <View style={styles.track}>
      <View style={[styles.fill, { width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }]} />
    </View>
  );
}

export function Row({ children, gap = space.md }: { children: ReactNode; gap?: number }) {
  return <View style={{ flexDirection: 'row', gap }}>{children}</View>;
}

/** Shared loading / error states for API-backed screens. */
export function LoadState({ loading, error, onRetry }: { loading: boolean; error?: string; onRetry?: () => void }) {
  if (error) {
    return (
      <View style={{ gap: space.md }}>
        <Notice title="Something went wrong" tone="danger">
          {error}
        </Notice>
        {onRetry && <Button label="Try again" variant="secondary" onPress={onRetry} />}
      </View>
    );
  }
  if (loading) return <ActivityIndicator style={{ marginTop: space.xl }} color={colors.primary} />;
  return null;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
  },
  back: { width: 32, height: 32, justifyContent: 'center' },
  body: { flex: 1 },
  bodyContent: { padding: space.xl, paddingTop: space.sm, gap: space.md },
  footer: { paddingHorizontal: space.xl, paddingTop: space.md, paddingBottom: space.xl, gap: space.md },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.lg,
  },
  button: { height: 52, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', paddingHorizontal: space.lg },
  buttonText: { fontSize: 17, fontWeight: '600' },
  chip: { borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 4, alignSelf: 'flex-start' },
  chipText: { fontSize: 13, fontWeight: '600' },
  notice: { flexDirection: 'row', gap: space.sm, borderRadius: radius.md, padding: space.lg },
  track: { height: 8, borderRadius: 4, backgroundColor: colors.primarySoft, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4, backgroundColor: colors.primary },
});
