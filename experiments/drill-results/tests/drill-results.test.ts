import { describe, expect, it } from 'vitest';
import { analyzeSession, SessionValidationError } from '../src/domain/drill-results';
import { formatSuccessRate } from '../src/format';

// These expectations come from the assignment's hand calculations. The input
// helper belongs to the tests, not the application's demonstration fixtures.
function session(outcomes: string[]) {
  return {
    sessionId: 'test-session',
    drillName: 'Test drill',
    recordedAt: '2026-11-15T15:00:00Z',
    dataSource: 'sample',
    attempts: outcomes.map((outcome, index) => ({
      attemptId: `a${index + 1}`,
      outcome,
      ...(['invalid_feed', 'uncertain'].includes(outcome)
        ? { exclusionReason: `Test exclusion ${index + 1}` }
        : {}),
    })),
  };
}

describe('session calculations', () => {
  it.each([
    {
      name: 'mixed outcomes',
      outcomes: ['successful', 'successful', 'successful', 'unsuccessful', 'invalid_feed', 'uncertain'],
      expected: { totalAttempts: 6, scoredAttempts: 4, excludedAttempts: 2, successRate: 75,
        outcomeCounts: { successful: 3, unsuccessful: 1, invalid_feed: 1, uncertain: 1 } },
    },
    {
      name: 'all successful', outcomes: ['successful', 'successful'],
      expected: { totalAttempts: 2, scoredAttempts: 2, excludedAttempts: 0, successRate: 100,
        outcomeCounts: { successful: 2, unsuccessful: 0, invalid_feed: 0, uncertain: 0 } },
    },
    {
      name: 'all unsuccessful', outcomes: ['unsuccessful', 'unsuccessful', 'unsuccessful'],
      expected: { totalAttempts: 3, scoredAttempts: 3, excludedAttempts: 0, successRate: 0,
        outcomeCounts: { successful: 0, unsuccessful: 3, invalid_feed: 0, uncertain: 0 } },
    },
    {
      name: 'all excluded', outcomes: ['invalid_feed', 'uncertain'],
      expected: { totalAttempts: 2, scoredAttempts: 0, excludedAttempts: 2, successRate: null,
        outcomeCounts: { successful: 0, unsuccessful: 0, invalid_feed: 1, uncertain: 1 } },
    },
    {
      name: 'empty', outcomes: [],
      expected: { totalAttempts: 0, scoredAttempts: 0, excludedAttempts: 0, successRate: null,
        outcomeCounts: { successful: 0, unsuccessful: 0, invalid_feed: 0, uncertain: 0 } },
    },
  ])('$name', ({ outcomes, expected }) => {
    expect(analyzeSession(session(outcomes)).summary).toEqual(expected);
  });

  it('preserves precision until display', () => {
    const { summary } = analyzeSession(session(['successful', 'unsuccessful', 'unsuccessful']));
    expect(summary.successRate).toBe((1 / 3) * 100);
    expect(summary.successRate).not.toBe(33.3);
    expect(formatSuccessRate(summary.successRate)).toBe('33.3%');
  });

  it.each([[75, '75%'], [100, '100%'], [0, '0%'], [null, 'N/A']] as const)(
    'formats %s as %s', (value, display) => expect(formatSuccessRate(value)).toBe(display),
  );

  it('preserves attempts and exclusion reasons without mutating input', () => {
    const input = session(['invalid_feed', 'uncertain', 'successful']);
    const original = structuredClone(input);
    input.attempts.forEach(Object.freeze);
    Object.freeze(input.attempts);
    Object.freeze(input);
    expect(analyzeSession(input).session.attempts).toEqual(original.attempts);
    expect(input).toEqual(original);
  });

  it('can summarize supplied results independently of the sample data source', () => {
    expect(analyzeSession({ ...session(['successful']), dataSource: 'external-test-source' }).summary.successRate).toBe(100);
  });
});

describe('input validation', () => {
  it.each([null, undefined, false, 42, 'session', []])('rejects a non-object session: %s', (input) => {
    expect(() => analyzeSession(input)).toThrow(SessionValidationError);
  });

  it.each(['sessionId', 'drillName', 'recordedAt', 'dataSource'])('requires %s', (field) => {
    const input: Record<string, unknown> = session([]);
    delete input[field];
    expect(() => analyzeSession(input)).toThrow(field);
  });

  it.each(['sessionId', 'drillName', 'recordedAt', 'dataSource'])('checks the type and content of %s', (field) => {
    for (const value of [null, 4, false, [], {}, '', '   ']) {
      expect(() => analyzeSession({ ...session([]), [field]: value })).toThrow(field);
    }
  });

  it.each([undefined, null, {}, 'attempts', 1])('requires an attempts array: %s', (attempts) => {
    expect(() => analyzeSession({ ...session([]), attempts })).toThrow('attempts');
  });

  it.each([null, undefined, 1, 'attempt', []])('rejects a malformed attempt: %s', (attempt) => {
    expect(() => analyzeSession({ ...session([]), attempts: [attempt] })).toThrow('attempts[0]');
  });

  it('rejects holes in an attempts array rather than skipping them', () => {
    expect(() => analyzeSession({ ...session([]), attempts: new Array(1) })).toThrow('attempts[0]');
  });

  it.each([undefined, null, '', '  ', 1, false, [], {}])('rejects invalid attempt IDs: %s', (attemptId) => {
    expect(() => analyzeSession({ ...session([]), attempts: [{ attemptId, outcome: 'successful' }] })).toThrow('attempts[0].attemptId');
  });

  it.each([undefined, null, 1, {}, [], 'success', 'Successful', 'unknown', '__proto__'])('rejects invalid outcomes: %s', (outcome) => {
    expect(() => analyzeSession({ ...session([]), attempts: [{ attemptId: 'a1', outcome }] })).toThrow('attempts[0].outcome');
  });

  it('rejects duplicate IDs within a session, even with different outcomes', () => {
    expect(() => analyzeSession({ ...session([]), attempts: [
      { attemptId: 'a1', outcome: 'successful' },
      { attemptId: 'a1', outcome: 'unsuccessful' },
    ] })).toThrow('attempts[1].attemptId');
  });

  it('allows the same attempt IDs in separate sessions', () => {
    expect(analyzeSession(session(['successful'])).summary.totalAttempts).toBe(1);
    expect(analyzeSession({ ...session(['unsuccessful']), sessionId: 'other-session' }).summary.totalAttempts).toBe(1);
  });

  it.each(['invalid_feed', 'uncertain'])('requires a nonblank reason for %s', (outcome) => {
    for (const exclusionReason of [undefined, null, '', '  ', 5, [], {}]) {
      expect(() => analyzeSession({ ...session([]), attempts: [{ attemptId: 'a1', outcome, exclusionReason }] })).toThrow('attempts[0].exclusionReason');
    }
  });

  it('validates an optional reason if supplied for a scored attempt', () => {
    expect(() => analyzeSession({ ...session([]), attempts: [
      { attemptId: 'a1', outcome: 'successful', exclusionReason: 7 },
    ] })).toThrow('attempts[0].exclusionReason');
  });

  it.each([
    'not-a-date', '2026-11-15', '2026-11-15T15:00:00', '2026-02-30T15:00:00Z',
    '2026-02-29T15:00:00Z', '2026-13-01T15:00:00Z', '2026-11-15T24:00:00Z',
    '2026-11-15T15:60:00Z', '2026-11-15T15:00:00+24:00',
  ])('rejects invalid or ambiguous timestamps: %s', (recordedAt) => {
    expect(() => analyzeSession({ ...session([]), recordedAt })).toThrow('recordedAt');
  });

  it.each(['2024-02-29T15:00:00Z', '2026-11-15T10:00:00-05:00', '2026-11-15T15:00:00.123Z'])(
    'accepts valid timestamps: %s', (recordedAt) => {
      expect(analyzeSession({ ...session([]), recordedAt }).session.recordedAt).toBe(recordedAt);
    },
  );

  it('reports all invalid records with field paths instead of returning a partial summary', () => {
    try {
      analyzeSession({ ...session([]), attempts: [
        { attemptId: 'a1', outcome: 'successful' },
        { attemptId: 'a2', outcome: 'unknown' },
        { attemptId: 'a3', outcome: 'uncertain' },
      ] });
      expect.fail('Expected validation failure');
    } catch (error) {
      expect(error).toBeInstanceOf(SessionValidationError);
      expect((error as SessionValidationError).issues.map((issue) => issue.path)).toEqual([
        'attempts[1].outcome', 'attempts[2].exclusionReason',
      ]);
    }
  });
});
