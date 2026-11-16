export const OUTCOMES = ['successful', 'unsuccessful', 'invalid_feed', 'uncertain'] as const;
export type Outcome = typeof OUTCOMES[number];

export type Attempt = { readonly attemptId: string } & (
  | { readonly outcome: 'successful' | 'unsuccessful'; readonly exclusionReason?: string }
  | { readonly outcome: 'invalid_feed' | 'uncertain'; readonly exclusionReason: string }
);

export interface DrillSession {
  readonly sessionId: string;
  readonly drillName: string;
  readonly recordedAt: string;
  readonly dataSource: string;
  readonly attempts: readonly Attempt[];
}

export interface SessionSummary {
  totalAttempts: number;
  scoredAttempts: number;
  excludedAttempts: number;
  successRate: number | null;
  outcomeCounts: Record<Outcome, number>;
}

export interface ValidationIssue { path: string; message: string }

export class SessionValidationError extends Error {
  readonly issues: readonly ValidationIssue[];

  constructor(issues: ValidationIssue[]) {
    super(issues.map(({ path, message }) => `${path}: ${message}`).join('\n'));
    this.name = 'SessionValidationError';
    this.issues = issues;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNonblankString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

// Reject ambiguous dates and calendar rollovers such as February 30.
function isTimestamp(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-](\d{2}):(\d{2}))$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1]!
    && Number(match[4]) <= 23 && Number(match[5]) <= 59 && Number(match[6]) <= 59
    && (match[7] === 'Z' || (Number(match[8]) <= 23 && Number(match[9]) <= 59))
    && Number.isFinite(Date.parse(value));
}

export function validateSession(input: unknown): DrillSession {
  if (!isRecord(input)) {
    throw new SessionValidationError([{ path: 'session', message: 'Expected a session object.' }]);
  }
  const issues: ValidationIssue[] = [];
  for (const field of ['sessionId', 'drillName', 'recordedAt', 'dataSource']) {
    if (!isNonblankString(input[field])) {
      issues.push({ path: field, message: 'Expected a nonblank string.' });
    }
  }
  if (isNonblankString(input.recordedAt) && !isTimestamp(input.recordedAt)) {
    issues.push({ path: 'recordedAt', message: 'Expected a valid ISO timestamp with seconds and a timezone, such as 2026-11-15T15:00:00Z.' });
  }
  if (!Array.isArray(input.attempts)) {
    issues.push({ path: 'attempts', message: 'Expected an array of attempts.' });
  } else {
    const ids = new Set<string>();
    for (let index = 0; index < input.attempts.length; index++) {
      const attempt: unknown = input.attempts[index];
      const path = `attempts[${index}]`;
      if (!isRecord(attempt)) {
        issues.push({ path, message: 'Expected an attempt object.' });
        continue;
      }
      if (!isNonblankString(attempt.attemptId)) {
        issues.push({ path: `${path}.attemptId`, message: 'Expected a nonblank string.' });
      } else if (ids.has(attempt.attemptId)) {
        issues.push({ path: `${path}.attemptId`, message: 'Attempt IDs must be unique within a session.' });
      } else {
        ids.add(attempt.attemptId);
      }
      if (!OUTCOMES.includes(attempt.outcome as Outcome)) {
        issues.push({ path: `${path}.outcome`, message: 'Expected successful, unsuccessful, invalid_feed, or uncertain.' });
      }
      const excluded = attempt.outcome === 'invalid_feed' || attempt.outcome === 'uncertain';
      if ((excluded || 'exclusionReason' in attempt) && !isNonblankString(attempt.exclusionReason)) {
        issues.push({ path: `${path}.exclusionReason`, message: 'Expected a nonblank exclusion reason.' });
      }
    }
  }
  if (issues.length > 0) throw new SessionValidationError(issues);
  return input as unknown as DrillSession;
}

/** Validate the entire supplied result before counting any attempts. */
export function analyzeSession(input: unknown): { session: DrillSession; summary: SessionSummary } {
  const session = validateSession(input);
  const outcomeCounts: Record<Outcome, number> = {
    successful: 0, unsuccessful: 0, invalid_feed: 0, uncertain: 0,
  };
  for (const attempt of session.attempts) outcomeCounts[attempt.outcome]++;
  const scoredAttempts = outcomeCounts.successful + outcomeCounts.unsuccessful;
  return {
    session,
    summary: {
      totalAttempts: session.attempts.length,
      scoredAttempts,
      excludedAttempts: outcomeCounts.invalid_feed + outcomeCounts.uncertain,
      successRate: scoredAttempts === 0 ? null : (outcomeCounts.successful / scoredAttempts) * 100,
      outcomeCounts,
    },
  };
}
