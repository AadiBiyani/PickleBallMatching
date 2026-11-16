import { describe, expect, it } from 'vitest';
import { analyzeSession } from '../src/domain/drill-results';
import { exampleSessions } from '../src/fixtures/sessions';

describe('demonstration fixtures', () => {
  it('uses unique session IDs and marks every example as sample data', () => {
    const sessions = exampleSessions.map(({ session }) => session as Record<string, unknown>);
    expect(new Set(sessions.map(({ sessionId }) => sessionId)).size).toBe(sessions.length);
    for (const session of sessions) expect(session.dataSource).toBe('sample');
  });

  it('keeps the supplied main fixture intact', () => {
    expect(exampleSessions.find(({ key }) => key === 'mixed')?.session).toEqual({
      sessionId: 'sample-session-001',
      drillName: 'Sample pickleball drill',
      recordedAt: '2026-11-15T15:00:00Z',
      dataSource: 'sample',
      attempts: [
        { attemptId: 'a1', outcome: 'successful' },
        { attemptId: 'a2', outcome: 'successful' },
        { attemptId: 'a3', outcome: 'successful' },
        { attemptId: 'a4', outcome: 'unsuccessful' },
        { attemptId: 'a5', outcome: 'invalid_feed', exclusionReason: 'Sample feed landed outside the prescribed area.' },
        { attemptId: 'a6', outcome: 'uncertain', exclusionReason: 'Sample ball-return outcome could not be determined.' },
      ],
    });
  });

  it('validates normal examples and rejects the deliberate invalid-data example', () => {
    for (const example of exampleSessions) {
      if (example.key === 'invalid') {
        expect(() => analyzeSession(example.session)).toThrow('outcome');
      } else {
        expect(() => analyzeSession(example.session)).not.toThrow();
      }
    }
  });
});
