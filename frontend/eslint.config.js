const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  { ignores: ['dist/**', '.expo/**'] },
  // Existing screens intentionally use ordinary apostrophes in JSX prose.
  { rules: { 'react/no-unescaped-entities': 'off' } },
  // Baseline screens predate lint setup; report their existing effect pattern
  // without requiring an unrelated recording/flagging/data-hook rewrite here.
  {
    files: ['src/app/record/recording.tsx', 'src/app/session/**/attempts.tsx', 'src/lib/hooks.ts'],
    rules: { 'react-hooks/set-state-in-effect': 'warn' },
  },
]);
