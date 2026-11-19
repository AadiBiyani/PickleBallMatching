import Svg, { Circle, Path } from 'react-native-svg';

import { colors } from '@/lib/theme';

interface IconProps {
  size?: number;
  color?: string;
}

export function ChevronLeft({ size = 22, color = colors.text }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M15 5l-7 7 7 7" stroke={color} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function ChevronRight({ size = 20, color = colors.muted }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M9 5l7 7-7 7" stroke={color} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function Check({ size = 14, color = '#fff' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M5 12.5l4.5 4.5L19 7.5" stroke={color} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function Cross({ size = 14, color = '#fff' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M6 6l12 12M18 6L6 18" stroke={color} strokeWidth={3} strokeLinecap="round" />
    </Svg>
  );
}

export function Flag({ size = 18, color = colors.muted, filled = false }: IconProps & { filled?: boolean }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M5 21V4m0 0h11l-2 4 2 4H5"
        stroke={color}
        fill={filled ? color : 'none'}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
}

export function StatusDot({ color, size = 10 }: { color: string; size?: number }) {
  return (
    <Svg width={size} height={size}>
      <Circle cx={size / 2} cy={size / 2} r={size / 2} fill={color} />
    </Svg>
  );
}

/** Small court glyph used on the drill list (matches the Figma drill icon). */
export function CourtGlyph({ size = 30 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 30 30" fill="none">
      <Path d="M6 3h18v24H6z" stroke={colors.primary} strokeWidth={1.8} />
      <Path d="M6 15h18M6 10h18M6 20h18M15 3v7M15 20v7" stroke={colors.primary} strokeWidth={1.4} />
      <Circle cx={20} cy={23} r={3} fill={colors.accent} stroke="#7C8A12" strokeWidth={1} />
    </Svg>
  );
}
