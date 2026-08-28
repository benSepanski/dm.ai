// TS strictness constraints from .checkpoints/architecture/chargen-fighter.md:
// no `any`, no raw wasm-bindgen imports outside the façade, no importing
// rules-data. The UI renders engine output; it computes no game values.
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist/**', 'src/engine/pkg/**', 'playwright-report/**', 'test-results/**'] },
  ...tseslint.configs.recommended,
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
  {
    // Everything outside the façade: engine access only through src/engine.
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/engine/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['**/pkg/*', '**/pkg'],
              message:
                'Raw wasm-bindgen output is private to the façade — import from src/engine instead.',
            },
            {
              group: ['**/rules-data/*', '**/rules-data'],
              message:
                'The UI never reads rules data — game knowledge arrives through the engine.',
            },
          ],
        },
      ],
    },
  },
);
