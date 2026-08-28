import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Vitest globals are off, so testing-library's automatic cleanup never
// registers itself; do it explicitly.
afterEach(() => {
  cleanup();
});
