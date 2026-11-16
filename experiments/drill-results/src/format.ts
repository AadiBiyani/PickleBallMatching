import type { Outcome } from './domain/drill-results';

export const outcomeLabels: Record<Outcome, string> = {
  successful: 'Successful',
  unsuccessful: 'Unsuccessful',
  invalid_feed: 'Invalid feed',
  uncertain: 'Uncertain',
};

const percentage = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });
export function formatSuccessRate(value: number | null): string {
  return value === null ? 'N/A' : `${percentage.format(value)}%`;
}

export function formatRecordedAt(value: string): string {
  return `${new Intl.DateTimeFormat('en-US', {
    dateStyle: 'long', timeStyle: 'short', timeZone: 'UTC',
  }).format(new Date(value))} UTC`;
}
