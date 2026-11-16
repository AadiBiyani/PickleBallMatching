import './styles.css';
import { analyzeSession, OUTCOMES, SessionValidationError } from './domain/drill-results';
import type { DrillSession } from './domain/drill-results';
import { exampleSessions } from './fixtures/sessions';
import { formatRecordedAt, formatSuccessRate, outcomeLabels } from './format';

function element<T extends HTMLElement = HTMLElement>(selector: string): T {
  const result = document.querySelector<T>(selector);
  if (!result) throw new Error(`Missing page element: ${selector}`);
  return result;
}

const selector = element<HTMLSelectElement>('#session-select');
const filter = element<HTMLSelectElement>('#outcome-filter');
const results = element('#results');
const errorPanel = element('#validation-error');
const attemptList = element<HTMLOListElement>('#attempt-list');
let currentSession: DrillSession | null = null;

for (const example of exampleSessions) {
  const option = document.createElement('option');
  option.value = example.key;
  option.textContent = example.label;
  selector.append(option);
}

function renderAttempts(): void {
  if (!currentSession) return;
  const attempts = currentSession.attempts.filter((attempt) => filter.value === 'all' || attempt.outcome === filter.value);
  const rows = attempts.map((attempt) => {
    const row = document.createElement('li');
    row.className = 'attempt-row';
    const id = document.createElement('span');
    id.className = 'attempt-id';
    id.textContent = `Attempt ${attempt.attemptId}`;
    const outcome = document.createElement('span');
    outcome.className = `outcome ${attempt.outcome}`;
    outcome.textContent = outcomeLabels[attempt.outcome];
    const note = document.createElement('span');
    note.className = 'attempt-note';
    note.textContent = attempt.outcome === 'invalid_feed' || attempt.outcome === 'uncertain'
      ? attempt.exclusionReason : 'Included in success rate.';
    row.append(id, outcome, note);
    return row;
  });
  attemptList.replaceChildren(...rows);
  element('#list-status').textContent = `Showing ${attempts.length} of ${currentSession.attempts.length} attempts. Session summary includes all outcomes.`;
  const emptySession = currentSession.attempts.length === 0;
  element('#empty-state').hidden = attempts.length > 0;
  element('#empty-title').textContent = emptySession ? 'No attempts yet.' : 'No attempts match this filter.';
  element('#empty-note').textContent = emptySession
    ? 'This sample session has no attempt records. Choose another example to explore results.'
    : 'Choose another outcome or select All outcomes to see the full list.';
}

function selectSession(): void {
  // Clear old data first so malformed input cannot leave a previous result visible.
  currentSession = null;
  results.hidden = true;
  errorPanel.hidden = true;
  attemptList.replaceChildren();
  filter.value = 'all';
  const example = exampleSessions.find(({ key }) => key === selector.value);
  try {
    const { session, summary } = analyzeSession(example?.session);
    currentSession = session;
    element('#session-title').textContent = session.drillName;
    element('#session-id').textContent = session.sessionId;
    const time = element<HTMLTimeElement>('#recorded-at');
    time.dateTime = session.recordedAt;
    time.textContent = formatRecordedAt(session.recordedAt);
    element('[data-testid="total"]').textContent = String(summary.totalAttempts);
    element('[data-testid="scored"]').textContent = String(summary.scoredAttempts);
    element('[data-testid="excluded"]').textContent = String(summary.excludedAttempts);
    element('[data-testid="success-rate"]').textContent = formatSuccessRate(summary.successRate);
    element('#rate-note').textContent = summary.successRate === null
      ? 'No scored attempts available.'
      : `${summary.outcomeCounts.successful} successful / ${summary.scoredAttempts} scored`;
    for (const outcome of OUTCOMES) {
      element(`[data-outcome-count="${outcome}"]`).textContent = String(summary.outcomeCounts[outcome]);
    }
    results.hidden = false;
    renderAttempts();
  } catch (error) {
    if (!(error instanceof SessionValidationError)) throw error;
    const issues = error.issues.map(({ path, message }) => {
      const item = document.createElement('li');
      item.textContent = `${path}: ${message}`;
      return item;
    });
    element('#validation-issues').replaceChildren(...issues);
    errorPanel.hidden = false;
  }
}

selector.addEventListener('change', selectSession);
filter.addEventListener('change', renderAttempts);
selectSession();
