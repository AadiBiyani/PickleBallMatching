import type { SelectionControlProps } from './SelectionControl';

/** Native HTML activation supplies both Space and Enter for the web demo. */
export function SelectionControl({ label, checked, onPress, disabled, role, children }: SelectionControlProps) {
  return <button type="button" role={role} aria-label={label} aria-checked={checked} disabled={disabled} onClick={onPress}
    style={{ display: 'block', width: '100%', border: 0, padding: 0, background: 'transparent', textAlign: 'left', font: 'inherit', cursor: disabled ? 'default' : 'pointer' }}>{children}</button>;
}
