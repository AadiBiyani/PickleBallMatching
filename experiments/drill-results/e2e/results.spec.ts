import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

async function expectSummary(page: Page, values: [string, string, string, string]) {
  const fields = ['total', 'scored', 'excluded', 'success-rate'];
  for (const [index, field] of fields.entries()) {
    await expect(page.getByTestId(field)).toHaveText(values[index]!);
  }
}

test.beforeEach(async ({ page }) => {
  page.on('pageerror', (error) => { throw error; });
  await page.goto('/');
});

test('shows the mixed results and exact exclusions with explicit sample provenance', async ({ page }, testInfo) => {
  await expect(page.getByText('Sample data', { exact: true })).toBeVisible();
  await expect(page.getByText('These examples are synthetic. No recording was analyzed.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Sample pickleball drill' })).toBeVisible();
  await expect(page.locator('time')).toHaveAttribute('datetime', '2026-11-15T15:00:00Z');
  await expect(page.locator('time')).toContainText('November 15, 2026');
  await expect(page.locator('time')).toContainText('UTC');
  await expectSummary(page, ['6', '4', '2', '75%']);
  for (const [outcome, count] of [['successful', '3'], ['unsuccessful', '1'], ['invalid_feed', '1'], ['uncertain', '1']]) {
    await expect(page.locator(`[data-outcome-count="${outcome}"]`)).toHaveText(count!);
  }
  const attempts = page.getByRole('list', { name: 'Drill attempts' });
  await expect(attempts.getByRole('listitem')).toHaveCount(6);
  await expect(attempts.getByRole('listitem').filter({ hasText: 'Attempt a5' })).toContainText('Sample feed landed outside the prescribed area.');
  await expect(attempts.getByRole('listitem').filter({ hasText: 'Attempt a6' })).toContainText('Sample ball-return outcome could not be determined.');
  await expect(attempts.getByRole('listitem').filter({ hasText: 'Attempt a5' })).not.toContainText('could not be determined');
  await page.screenshot({ path: testInfo.outputPath('mixed-results.png'), fullPage: true });
});

test('each filter changes only the list and reports no matching attempts distinctly', async ({ page }) => {
  const originalSummary = await page.locator('#summary').innerText();
  for (const [filter, ids] of [
    ['successful', ['a1', 'a2', 'a3']], ['unsuccessful', ['a4']],
    ['invalid_feed', ['a5']], ['uncertain', ['a6']], ['all', ['a1', 'a2', 'a3', 'a4', 'a5', 'a6']],
  ] as const) {
    await page.getByLabel('Filter by outcome').selectOption(filter);
    await expect(page.locator('#attempt-list li')).toHaveCount(ids.length);
    await expect(page.locator('#attempt-list .attempt-id')).toHaveText(ids.map((id) => `Attempt ${id}`));
    await expect(page.locator('#summary')).toHaveText(originalSummary, { useInnerText: true });
  }
  await page.getByLabel('Example session').selectOption('all-successful');
  await page.getByLabel('Filter by outcome').selectOption('uncertain');
  await expect(page.getByText('No attempts match this filter.')).toBeVisible();
  await expectSummary(page, ['2', '2', '0', '100%']);
  await expect(page.getByText('No attempts yet.', { exact: true })).not.toBeVisible();
});

test('switches all fixtures, updates metadata and counts, and resets the filter', async ({ page }, testInfo) => {
  const examples = [
    { key: 'all-successful', title: 'Sample successful returns', id: 'sample-session-002', values: ['2', '2', '0', '100%'], counts: ['2', '0', '0', '0'] },
    { key: 'all-unsuccessful', title: 'Sample unsuccessful returns', id: 'sample-session-003', values: ['3', '3', '0', '0%'], counts: ['0', '3', '0', '0'] },
    { key: 'all-excluded', title: 'Sample excluded attempts', id: 'sample-session-004', values: ['2', '0', '2', 'N/A'], counts: ['0', '0', '1', '1'] },
    { key: 'empty', title: 'Sample empty session', id: 'sample-session-005', values: ['0', '0', '0', 'N/A'], counts: ['0', '0', '0', '0'] },
    { key: 'rounding', title: 'Sample one-third success', id: 'sample-session-006', values: ['3', '3', '0', '33.3%'], counts: ['1', '2', '0', '0'] },
  ];
  for (const example of examples) {
    await page.getByLabel('Filter by outcome').selectOption('invalid_feed');
    await page.getByLabel('Example session').selectOption(example.key);
    await expect(page.getByLabel('Filter by outcome')).toHaveValue('all');
    await expect(page.getByRole('heading', { name: example.title })).toBeVisible();
    await expect(page.locator('#session-id')).toHaveText(example.id);
    const expectedTimes: Record<string, string> = {
      'all-successful': '2026-11-15T15:10:00Z', 'all-unsuccessful': '2026-11-15T15:20:00Z',
      'all-excluded': '2026-11-15T15:30:00Z', empty: '2026-11-15T15:40:00Z', rounding: '2026-11-15T15:50:00Z',
    };
    await expect(page.locator('time')).toHaveAttribute('datetime', expectedTimes[example.key]!);
    await expectSummary(page, example.values as [string, string, string, string]);
    await expect(page.locator('[data-outcome-count]')).toHaveText(example.counts);
    await expect(page.locator('#attempt-list li')).toHaveCount(Number(example.values[0]));
    if (example.values[3] === 'N/A') {
      await expect(page.getByText('No scored attempts available.')).toBeVisible();
      if (example.key === 'all-excluded') {
        await page.screenshot({ path: testInfo.outputPath('all-excluded.png'), fullPage: true });
      }
    } else {
      await expect(page.getByText('No scored attempts available.')).not.toBeVisible();
    }
    if (example.key === 'empty') await expect(page.getByText('No attempts yet.', { exact: true })).toBeVisible();
  }
});

test('shows an actionable invalid-data state without stale results and recovers', async ({ page }, testInfo) => {
  await page.getByLabel('Example session').selectOption('invalid');
  const error = page.getByRole('alert');
  await expect(error).toContainText('This example contains invalid data');
  await expect(error).toContainText('attempts[1].outcome');
  await expect(error).toContainText('Choose another example session');
  await expect(page.locator('#results')).toBeHidden();
  await expect(page.locator('#attempt-list li')).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath('invalid-data.png'), fullPage: true });
  await page.getByLabel('Example session').selectOption('mixed');
  await expect(error).toBeHidden();
  await expectSummary(page, ['6', '4', '2', '75%']);
});

test('native selectors work with a keyboard and keep visible focus', async ({ page }) => {
  const selector = page.getByLabel('Example session');
  await selector.focus();
  await expect(selector).toBeFocused();
  // Exercise native keyboard typeahead without depending on the OS popup menu.
  await page.keyboard.press('a');
  await expect(selector).toHaveValue('all-successful');
  await expectSummary(page, ['2', '2', '0', '100%']);
  await page.keyboard.press('Tab');
  const filter = page.getByLabel('Filter by outcome');
  await expect(filter).toBeFocused();
  await expect(filter).toHaveCSS('outline-style', 'solid');
  await page.keyboard.press('s');
  await expect(filter).toHaveValue('successful');
  await expect(page.locator('#attempt-list li')).toHaveCount(2);
});

test('fits a narrow screen and keeps controls and exclusion reasons readable', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await expect(page.getByLabel('Example session')).toBeVisible();
  await expect(page.getByLabel('Filter by outcome')).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('narrow-results.png'), fullPage: true });
  await page.getByLabel('Filter by outcome').selectOption('invalid_feed');
  await expect(page.locator('#attempt-list')).toContainText('Sample feed landed outside the prescribed area.');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByLabel('Example session').selectOption('invalid');
  await expect(page.getByRole('alert')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
