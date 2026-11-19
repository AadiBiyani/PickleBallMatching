// Colors and spacing taken from the Figma prototype.
export const colors = {
  bg: '#F4F4F0',
  card: '#FFFFFF',
  border: '#E3E3DD',
  text: '#16181D',
  muted: '#6B7280',
  primary: '#1D4ED8',
  primarySoft: '#E7EDFD',
  accent: '#D6EF3C',
  success: '#1E8E5A',
  successSoft: '#E3F3EA',
  danger: '#D63A2F',
  dangerSoft: '#FDE8E6',
  warning: '#B7791F',
  warningSoft: '#FFF4DC',
  disabled: '#E2E2DC',
  disabledText: '#8A8D93',
  camera: '#1F2731',
  courtFill: '#2C5E8C',
  courtLine: '#FFFFFF',
  insufficient: '#D9D9D3',
};

export const radius = { sm: 8, md: 14, lg: 20, pill: 999 };
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };

export const type = {
  title: { fontSize: 18, fontWeight: '600' as const, color: colors.text },
  h1: { fontSize: 26, fontWeight: '700' as const, color: colors.text },
  h2: { fontSize: 18, fontWeight: '700' as const, color: colors.text },
  body: { fontSize: 15, color: colors.text, lineHeight: 21 },
  small: { fontSize: 13, color: colors.muted, lineHeight: 18 },
  label: { fontSize: 12, fontWeight: '700' as const, color: colors.muted, letterSpacing: 0.6 },
  stat: { fontSize: 30, fontWeight: '700' as const, color: colors.text },
};

export const pct = (v: number | null | undefined) => (v == null ? '-' : `${Math.round(v * 100)}%`);
