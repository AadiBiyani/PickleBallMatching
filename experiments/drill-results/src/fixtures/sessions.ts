// Fabricated labels for development only. No recording or model produced them.
export interface ExampleSession { key: string; label: string; session: unknown }

export const exampleSessions: readonly ExampleSession[] = [
  {
    key: 'mixed', label: 'Mixed outcomes',
    session: {
      sessionId: 'sample-session-001', drillName: 'Sample pickleball drill',
      recordedAt: '2026-11-15T15:00:00Z', dataSource: 'sample',
      attempts: [
        { attemptId: 'a1', outcome: 'successful' },
        { attemptId: 'a2', outcome: 'successful' },
        { attemptId: 'a3', outcome: 'successful' },
        { attemptId: 'a4', outcome: 'unsuccessful' },
        { attemptId: 'a5', outcome: 'invalid_feed', exclusionReason: 'Sample feed landed outside the prescribed area.' },
        { attemptId: 'a6', outcome: 'uncertain', exclusionReason: 'Sample ball-return outcome could not be determined.' },
      ],
    },
  },
  {
    key: 'all-successful', label: 'All successful',
    session: {
      sessionId: 'sample-session-002', drillName: 'Sample successful returns',
      recordedAt: '2026-11-15T15:10:00Z', dataSource: 'sample',
      attempts: [{ attemptId: 'a1', outcome: 'successful' }, { attemptId: 'a2', outcome: 'successful' }],
    },
  },
  {
    key: 'all-unsuccessful', label: 'All unsuccessful',
    session: {
      sessionId: 'sample-session-003', drillName: 'Sample unsuccessful returns',
      recordedAt: '2026-11-15T15:20:00Z', dataSource: 'sample',
      attempts: [
        { attemptId: 'a1', outcome: 'unsuccessful' },
        { attemptId: 'a2', outcome: 'unsuccessful' },
        { attemptId: 'a3', outcome: 'unsuccessful' },
      ],
    },
  },
  {
    key: 'all-excluded', label: 'All excluded',
    session: {
      sessionId: 'sample-session-004', drillName: 'Sample excluded attempts',
      recordedAt: '2026-11-15T15:30:00Z', dataSource: 'sample',
      attempts: [
        { attemptId: 'a1', outcome: 'invalid_feed', exclusionReason: 'Sample feed landed outside the prescribed area.' },
        { attemptId: 'a2', outcome: 'uncertain', exclusionReason: 'Sample ball-return outcome could not be determined.' },
      ],
    },
  },
  {
    key: 'empty', label: 'Empty session',
    session: {
      sessionId: 'sample-session-005', drillName: 'Sample empty session',
      recordedAt: '2026-11-15T15:40:00Z', dataSource: 'sample', attempts: [],
    },
  },
  {
    key: 'rounding', label: 'One-third success',
    session: {
      sessionId: 'sample-session-006', drillName: 'Sample one-third success',
      recordedAt: '2026-11-15T15:50:00Z', dataSource: 'sample',
      attempts: [
        { attemptId: 'a1', outcome: 'successful' },
        { attemptId: 'a2', outcome: 'unsuccessful' },
        { attemptId: 'a3', outcome: 'unsuccessful' },
      ],
    },
  },
  {
    key: 'invalid', label: 'Invalid data example',
    session: {
      sessionId: 'sample-session-007', drillName: 'Sample invalid data',
      recordedAt: '2026-11-15T16:00:00Z', dataSource: 'sample',
      attempts: [{ attemptId: 'a1', outcome: 'successful' }, { attemptId: 'a2', outcome: 'unknown' }],
    },
  },
];
