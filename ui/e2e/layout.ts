// The layout sweep (architecture: chargen-wizard): three app-agnostic
// invariants asserted on the live DOM, callable from any story at any
// point. Violations report the guilty element's selector path.
import { expect, type Page } from '@playwright/test';

export interface LayoutViolation {
  kind: string;
  path: string;
  detail: string;
}

/** Collect layout violations in the current DOM state. */
export async function layoutViolations(page: Page): Promise<LayoutViolation[]> {
  return page.evaluate(() => {
    const violations: { kind: string; path: string; detail: string }[] = [];
    const pathOf = (el: Element): string => {
      const parts: string[] = [];
      let cur: Element | null = el;
      while (cur !== null && cur !== document.body && parts.length < 6) {
        const cls = [...cur.classList].slice(0, 2).join('.');
        parts.unshift(cur.tagName.toLowerCase() + (cls !== '' ? `.${cls}` : ''));
        cur = cur.parentElement;
      }
      return parts.join(' > ');
    };

    // (a) The document itself never scrolls horizontally.
    const doc = document.documentElement;
    if (doc.scrollWidth > doc.clientWidth + 1) {
      violations.push({
        kind: 'page-overflow',
        path: 'html',
        detail: `document scrollWidth ${doc.scrollWidth} > viewport ${doc.clientWidth}`,
      });
    }

    for (const el of Array.from(document.querySelectorAll('*'))) {
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') {
        continue;
      }
      // (b) Content never escapes a non-scrolling box horizontally.
      const overflowX = style.overflowX;
      if (
        (overflowX === 'visible' || overflowX === 'clip') &&
        el.scrollWidth > el.clientWidth + 1 &&
        el.clientWidth > 0
      ) {
        violations.push({
          kind: 'element-overflow',
          path: pathOf(el),
          detail: `scrollWidth ${el.scrollWidth} > clientWidth ${el.clientWidth}`,
        });
      }
    }

    // (c) Content columns must stay readable: a main content area
    // narrower than 45% of the viewport (or 320px, whichever is smaller)
    // means the layout collapsed into a sliver — wrapping hides it from
    // the overflow checks, so measure it directly.
    for (const el of Array.from(
      document.querySelectorAll<HTMLElement>('.wizard-main, .sheet-page, .roster'),
    )) {
      const rect = el.getBoundingClientRect();
      const viewport = document.documentElement.clientWidth;
      const minimum = Math.min(viewport * 0.45, 320);
      if (rect.width > 0 && rect.width < minimum) {
        violations.push({
          kind: 'starved-column',
          path: pathOf(el),
          detail: `content column is ${Math.round(rect.width)}px wide in a ${viewport}px viewport`,
        });
      }
    }

    // (d) Every enabled control lies inside its clipping ancestor's box.
    const controls = document.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), select:not([disabled])',
    );
    for (const el of Array.from(controls)) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) {
        continue; // not rendered
      }
      let ancestor = el.parentElement;
      while (ancestor !== null && ancestor !== document.body) {
        const style = getComputedStyle(ancestor);
        const clips = style.overflowX === 'hidden' || style.overflowX === 'clip';
        if (clips) {
          const box = ancestor.getBoundingClientRect();
          if (rect.right > box.right + 1 || rect.left < box.left - 1) {
            violations.push({
              kind: 'clipped-control',
              path: pathOf(el),
              detail: `control [${rect.left},${rect.right}] escapes its clip box [${box.left},${box.right}]`,
            });
          }
          break;
        }
        ancestor = ancestor.parentElement;
      }
      // Also: a control pushed beyond the viewport's right edge is
      // unreachable in practice even if nothing technically clips it.
      if (rect.left > document.documentElement.clientWidth) {
        violations.push({
          kind: 'offscreen-control',
          path: pathOf(el),
          detail: `control starts at ${rect.left}, viewport is ${document.documentElement.clientWidth}`,
        });
      }
    }

    // (e) No dead controls: a disabled action button must explain itself
    // with visible text (aria-describedby → a rendered, non-empty
    // element). A control the player cannot use and cannot explain is a
    // bug even when the layout is pristine — the app marks transient
    // in-flight disables with data-busy, which are exempt.
    const actionButtons = document.querySelectorAll<HTMLButtonElement>(
      'button.confirm[disabled]:not([data-busy]), button.fill-remaining[disabled]:not([data-busy])',
    );
    for (const el of Array.from(actionButtons)) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) {
        continue;
      }
      const describedBy = el.getAttribute('aria-describedby');
      const target = describedBy !== null ? document.getElementById(describedBy) : null;
      const explained =
        target !== null &&
        (target.textContent ?? '').trim() !== '' &&
        target.getBoundingClientRect().height > 0;
      if (!explained) {
        violations.push({
          kind: 'dead-control',
          path: pathOf(el),
          detail: `disabled action "${(el.textContent ?? '').trim()}" has no visible explanation (aria-describedby)`,
        });
      }
    }
    return violations;
  });
}

/** Assert the current screen is layout-sane; call from any story step. */
export async function expectSaneLayout(page: Page): Promise<void> {
  const violations = await layoutViolations(page);
  expect(
    violations,
    `layout violations:\n${violations.map((v) => `  [${v.kind}] ${v.path} — ${v.detail}`).join('\n')}`,
  ).toEqual([]);
}
