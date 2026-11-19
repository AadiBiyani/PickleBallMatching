import type { ReactNode } from 'react';
import { Pressable } from 'react-native';

export interface SelectionControlProps {
  label: string;
  checked: boolean;
  onPress: () => void;
  disabled?: boolean;
  role: 'checkbox' | 'radio';
  children: ReactNode;
}

export function SelectionControl({ label, checked, onPress, disabled, role, children }: SelectionControlProps) {
  return <Pressable accessibilityLabel={label} accessibilityRole={role} accessibilityState={{ checked, disabled }} disabled={disabled} onPress={onPress}>{children}</Pressable>;
}
